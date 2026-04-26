import logging
import signal
import time
from multiprocessing import Event, Process
from multiprocessing.queues import Empty, Full, Queue

import numpy as np
from commpy.filters import rrcosfilter
from modem import Qam

from radiolab.app.sinks import ImageSink
from radiolab.config.config import PhyConfig
from radiolab.link.framer import Framer
from radiolab.link.scrambler import PayloadScrambler
from radiolab.phy.rx import ModemRx
from radiolab.phy.tx import NASA_CODEWORDS, int_to_m_bit_chunks

logger = logging.getLogger(__name__)


def _get_codeword(code_length, M):
    return np.array(
        int_to_m_bit_chunks(NASA_CODEWORDS[code_length], code_length, int(np.log2(M))),
        dtype=int,
    )


class RxWorker(Process):
    def __init__(
        self,
        rx_queue: Queue,
        gui_queue: Queue,
        config: PhyConfig,
        stop_event: Event,
        max_timeout: float,
        name: str = "RxWorker",
    ):
        """"""

        logger.info(f"{name} starting")

        super().__init__(name=name, daemon=True)
        self.rx_queue = rx_queue
        self.gui_queue = gui_queue
        self.config = config
        self.stop_event = stop_event
        self.max_timeout = max_timeout
        self.framer = Framer()
        self.image_sink = ImageSink()
        self.scrambler = PayloadScrambler(
            seed=self.config.scrambler_seed,
            polynomial=self.config.scrambler_polynomial,
            width=self.config.scrambler_width,
            enabled=self.config.scrambler_enabled,
        )
        self.ted_margin_symbols = 8
        self.rx_seq = 0
        self.debug_corr_slice_len = 400
        self.debug_pll_stat_slice_len = 1000
        self.debug_symbol_slice_len = 500
        self.debug_success_every_n = 10
        self.debug_plot_every_n = 5

        rrc, rrc_coeff = rrcosfilter(
            self.config.rrc_span * self.config.samples_per_symbol + 1,
            alpha=self.config.rrc_beta,
            Ts=self.config.samples_per_symbol,
            Fs=1.0,
        )

        try:
            qam = Qam(self.config.modulation_order)
        except Exception as exc:
            logger.exception(f"Failed to implement Cpp methods: {exc}")

        try:
            # Get codeword, and simulate that it has gone through modulation
            # Upsampling, pulse shaping, then down-sampled
            code = _get_codeword(
                self.config.codeword_length, self.config.modulation_order
            )
            modulated_code = np.asarray(qam.modulate_array(code), dtype=complex)

            upsampled_code = np.zeros_like(
                modulated_code,
                shape=(len(modulated_code) * self.config.samples_per_symbol,),
            )
            upsampled_code[:: self.config.samples_per_symbol] = modulated_code

            # Send the code through the pulse shaping and matched filter
            pulse_shaped_code = np.convolve(upsampled_code, rrc_coeff, mode="same")
            matched_filtered_code = np.convolve(
                pulse_shaped_code, rrc_coeff, mode="same"
            )
            self.code_os = matched_filtered_code
            self.code_sym = matched_filtered_code[:: self.config.samples_per_symbol]
            self.coarse_corr_threshold = (
                self.config.codeword_corr_threshold * self.config.samples_per_symbol
            )

        except Exception as exc:
            logger.exception(
                f"Failed to create codeword used for checking valid data: {exc}"
            )

        self.phy = ModemRx(qam, self.config.samples_per_symbol, rrc_coeff)

    def _emit_rx_debug(
        self,
        seq: int,
        ok: bool,
        reason: str,
        times_ms: dict,
        metadata: dict | None = None,
    ) -> None:
        msg = {
            "type": "rx_debug",
            "seq": seq,
            "timestamp_ns": time.perf_counter_ns(),
            "ok": ok,
            "reason": reason,
            "times_ms": times_ms,
            "decode": {
                "metadata_ok": metadata is not None,
                "metadata": metadata,
            },
        }

        try:
            self.gui_queue.put_nowait(msg)
        except Full:
            logger.warning("Dropping RX debug frame")

    def _emit_rx_debug_plot(self, seq: int, plot: str, data: np.ndarray) -> None:
        msg = {
            "type": "rx_debug_plot",
            "seq": seq,
            "plot": plot,
            "data": data,
        }
        try:
            self.gui_queue.put_nowait(msg)
        except Full:
            logger.warning("Dropping RX debug plot frame")

    def run(self) -> None:
        """"""

        signal.signal(signal.SIGINT, signal.SIG_IGN)

        while not self.stop_event.is_set():
            try:
                rx_data = self.rx_queue.get(timeout=self.max_timeout)
            except Empty:
                # logger.warning("No Rx data to fetch yet")
                continue

            try:
                seq = self.rx_seq
                self.rx_seq += 1

                start_time = time.perf_counter_ns()
                times_ms = {
                    "matched_filter": None,
                    "coarse_corr": None,
                    "coarse_detect": None,
                    "ted": None,
                    "fine_corr": None,
                    "fine_detect": None,
                    "remove_code": None,
                    "agc": None,
                    "pll": None,
                    "demod": None,
                    "total": None,
                }

                # Matched filtering
                matched_filtered_data = self.phy.matched_filtering(rx_data)
                matched_filter_time = time.perf_counter_ns()
                times_ms["matched_filter"] = (matched_filter_time - start_time) * 10e-6
                # matched_filtered_data = self.phy.coarse_frequency_offset(
                #     matched_filtered_data
                # )
                coarse_frequency_time = time.perf_counter_ns()

                # Coarse correlation (Is there any chance data is present)
                coarse_correlation = self.phy.correlate_with_codeword(
                    matched_filtered_data, self.code_os
                )
                coarse_correlation_time = time.perf_counter_ns()
                times_ms["coarse_corr"] = (
                    coarse_correlation_time - coarse_frequency_time
                ) * 10e-6

                coarse_peak_index, coarse_peak_val = self.phy.detect_peak(
                    coarse_correlation,
                    threshold=self.coarse_corr_threshold,
                )
                coarse_detect_time = time.perf_counter_ns()
                times_ms["coarse_detect"] = (
                    coarse_detect_time - coarse_correlation_time
                ) * 10e-6

                if coarse_peak_index is None:
                    if seq % self.debug_success_every_n == 0:
                        self._emit_rx_debug(
                            seq=seq,
                            ok=False,
                            reason="coarse_no_peak",
                            times_ms=times_ms,
                        )
                    continue

                coarse_start_index = self.phy.peak_to_start(
                    coarse_peak_index,
                    len(self.code_os),
                    len(matched_filtered_data),
                )
                ted_margin = self.ted_margin_symbols * self.config.samples_per_symbol
                ted_start = max(0, coarse_start_index - ted_margin)
                ted_input = matched_filtered_data[ted_start:]

                # Do timing error detection (downsampling)
                matched_filtered_data = self.phy.recover_timing(ted_input)
                timing_recovery_time = time.perf_counter_ns()
                times_ms["ted"] = (timing_recovery_time - coarse_detect_time) * 10e-6

                # Fine correlation to do symbol sync
                correlation = self.phy.correlate_with_codeword(
                    matched_filtered_data, self.code_sym
                )
                correlation_time = time.perf_counter_ns()
                times_ms["fine_corr"] = (
                    correlation_time - timing_recovery_time
                ) * 10e-6

                fine_peak_index, fine_peak_val = self.phy.detect_peak(
                    correlation,
                    threshold=self.config.codeword_corr_threshold,
                )
                detect_codeword_time = time.perf_counter_ns()
                times_ms["fine_detect"] = (
                    detect_codeword_time - correlation_time
                ) * 10e-6

                if fine_peak_index is None:
                    if seq % self.debug_success_every_n == 0:
                        self._emit_rx_debug(
                            seq=seq,
                            ok=False,
                            reason="fine_no_peak",
                            times_ms=times_ms,
                        )
                    continue

                start_of_data_index = self.phy.peak_to_start(
                    fine_peak_index,
                    len(self.code_sym),
                    len(matched_filtered_data),
                )

                # Remove codeword so we should be left with preamble, header and payload
                matched_filtered_data = self.phy.remove_codeword_from_start(
                    matched_filtered_data,
                    start_of_data_index,
                    len(self.code_sym),
                )
                remove_codeword_time = time.perf_counter_ns()
                times_ms["remove_code"] = (
                    remove_codeword_time - detect_codeword_time
                ) * 10e-6

                # Do automatic gain control
                matched_filtered_data, agc_gain = self.phy.automatic_gain_control(
                    matched_filtered_data,
                    preamble_length=self.config.pll_preamble_length,
                    target_magnitude=np.sqrt(2.0),
                )
                if matched_filtered_data is None:
                    self._emit_rx_debug(
                        seq=seq,
                        ok=False,
                        reason="agc_invalid_gain",
                        times_ms=times_ms,
                    )
                    continue
                agc_time = time.perf_counter_ns()
                times_ms["agc"] = (agc_time - remove_codeword_time) * 10e-6

                # Perform phase locked data and use the fact that we know
                # What the preamble should look like
                _preamble = np.array(
                    [1.0 + 1.0j, -1.0 + 1.0j, -1.0 - 1.0j, 1.0 - 1.0j]
                    * (self.config.pll_preamble_length // 4)
                )
                phase_locked_data, pll_error, pll_theta = (
                    self.phy.phase_locked_loop_with_stats(
                        matched_filtered_data,
                        pll_preamble=_preamble,
                    )
                )
                phase_locked_loop_time = time.perf_counter_ns()
                times_ms["pll"] = (phase_locked_loop_time - agc_time) * 10e-6

                # Demodulate data
                demodulated_symbols = np.asarray(
                    self.phy.qam.demodulate_array(
                        phase_locked_data[self.config.pll_preamble_length :]
                    ),
                    dtype=int,
                )
                demodulate_time = time.perf_counter_ns()
                times_ms["demod"] = (demodulate_time - phase_locked_loop_time) * 10e-6

                # Unpack frame and separate metadata and payload
                decoded_image = None
                metadata, framed_payload = self.framer.unpack_frame(
                    demodulated_symbols,
                    modulation_order=self.config.modulation_order,
                )
                if metadata is None:
                    times_ms["total"] = (time.perf_counter_ns() - start_time) * 10e-6
                    if seq % self.debug_plot_every_n == 0:
                        self._emit_rx_debug_plot(
                            seq=seq,
                            plot="correlation",
                            data=correlation[: self.debug_corr_slice_len],
                        )
                    self._emit_rx_debug(
                        seq=seq,
                        ok=False,
                        reason="header_decode_failed",
                        times_ms=times_ms,
                    )
                    continue
                else:
                    logger.info(f"Received metadata: {metadata}")
                    framed_payload = self.scrambler.descramble_symbols(
                        framed_payload, self.config.modulation_order
                    )
                    decoded_image = self.image_sink.decode_image(
                        metadata, framed_payload
                    )

                times_ms["total"] = (time.perf_counter_ns() - start_time) * 10e-6
                if seq % self.debug_plot_every_n == 0:
                    self._emit_rx_debug_plot(
                        seq=seq,
                        plot="correlation",
                        data=correlation[: self.debug_corr_slice_len],
                    )

                # Only send full PLL internals for frames that actually decode.
                self._emit_rx_debug_plot(
                    seq=seq,
                    plot="pll_error",
                    data=pll_error[: self.debug_pll_stat_slice_len],
                )
                self._emit_rx_debug_plot(
                    seq=seq,
                    plot="pll_theta",
                    data=pll_theta[: self.debug_pll_stat_slice_len],
                )
                if seq % self.debug_success_every_n == 0:
                    self._emit_rx_debug(
                        seq=seq,
                        ok=True,
                        reason="ok",
                        times_ms=times_ms,
                        metadata=metadata,
                    )

                logger.info(
                    f"Times: Matched filtering: {(matched_filter_time - start_time) * 10e-6:.3f} ms, "
                    + f"CFO: {(coarse_frequency_time - matched_filter_time) * 10e-6:.3f} ms, "
                    + f"COARSE CORR: {(coarse_correlation_time - coarse_frequency_time) * 10e-6:.3f} ms, "
                    + f"COARSE DETECT: {(coarse_detect_time - coarse_correlation_time) * 10e-6:.3f} ms, "
                    + f"TED: {(timing_recovery_time - coarse_detect_time) * 10e-6:.3f} ms, "
                    + f"FINE CORR: {(correlation_time - timing_recovery_time) * 10e-6:.3f} ms, "
                    + f"CODE: {(detect_codeword_time - correlation_time) * 10e-6:.3f} ms, "
                    + f"RM CODE: {(remove_codeword_time - detect_codeword_time) * 10e-6:.3f} ms, "
                    + f"AGC: {(agc_time - remove_codeword_time) * 10e-6:.3f} ms, "
                    + f"PLL: {(phase_locked_loop_time - agc_time) * 10e-6:.3f} ms, "
                    + f"DEMOD: {(demodulate_time - phase_locked_loop_time) * 10e-6:.3f} ms, "
                    + f"\nTotal: {(time.perf_counter_ns() - start_time) * 10e-9:.3f} s"
                )

            except Exception as exc:
                if self.stop_event.is_set():
                    logger.debug(f"Ignoring RX error during shutdown: {exc}")
                    break
                logger.exception(f"Failed while processing Rx data: {exc}")
                self._emit_rx_debug(
                    seq=seq,
                    ok=False,
                    reason="exception",
                    times_ms=times_ms,
                )
                continue

            try:
                self.gui_queue.put_nowait(
                    {
                        "type": "rx_update",
                        "matched_filtered_preview": matched_filtered_data[
                            self.config.pll_preamble_length :
                        ][: self.debug_symbol_slice_len],
                        "phase_locked_preview": phase_locked_data[
                            self.config.pll_preamble_length :
                        ][: self.debug_symbol_slice_len],
                        "rx_metadata": metadata,
                        "rx_image": decoded_image,
                        "rx_payload": framed_payload,
                        # "decoded_data": decoded_data,
                    }
                )
            except Full:
                logger.warning("Dropping RX GUI frame")
                pass
