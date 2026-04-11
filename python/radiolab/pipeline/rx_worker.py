import logging
import time
from multiprocessing import Event, Process
from multiprocessing.queues import Empty, Full, Queue

import numpy as np
from commpy.filters import rrcosfilter
from modem import Qam

from radiolab.config.config import PhyConfig
from radiolab.link.framer import Framer
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
            # Downsample
            self.code = matched_filtered_code[:: self.config.samples_per_symbol]

        except Exception as exc:
            logger.exception(
                f"Failed to create codeword used for checking valid data: {exc}"
            )

        self.phy = ModemRx(qam, self.config.samples_per_symbol, rrc_coeff)

    def run(self) -> None:
        """"""

        while not self.stop_event.is_set():
            try:
                rx_data = self.rx_queue.get(timeout=self.max_timeout)
            except Empty:
                # logger.warning("No Rx data to fetch yet")
                continue

            try:
                start_time = time.perf_counter_ns()
                matched_filtered_data = self.phy.matched_filtering(rx_data)
                matched_filter_time = time.perf_counter_ns()
                # matched_filtered_data = self.phy.coarse_frequency_offset(
                #     matched_filtered_data
                # )
                coarse_frequency_time = time.perf_counter_ns()

                matched_filtered_data = self.phy.recover_timing(matched_filtered_data)
                timing_recovery_time = time.perf_counter_ns()

                correlation = self.phy._correlate_with_codeword(
                    matched_filtered_data, self.code
                )
                correlation_time = time.perf_counter_ns()

                try:
                    start_of_data_index = self.phy.detect_codeword(
                        matched_filtered_data,
                        self.code,
                        threshold=self.config.codeword_corr_threshold,
                    )
                    detect_codeword_time = time.perf_counter_ns()

                    start_of_data_index = start_of_data_index[0]
                except IndexError:
                    # logger.info("No data found, dropping received data")
                    continue

                matched_filtered_data = self.phy.remove_codeword(
                    matched_filtered_data,
                    start_of_data_index,
                    len(self.code),
                )
                remove_codeword_time = time.perf_counter_ns()

                # Should be AGC
                matched_filtered_data /= np.max(matched_filtered_data)
                agc_time = time.perf_counter_ns()

                _preamble = np.array(
                    [1.0 + 1.0j, -1.0 + 1.0j, -1.0 - 1.0j, 1.0 - 1.0j]
                    * (self.config.pll_preamble_length // 4)
                )
                phase_locked_data = self.phy.phase_locked_loop(
                    matched_filtered_data, pll_preamble=_preamble
                )
                phase_locked_loop_time = time.perf_counter_ns()

                demodulated_symbols = np.asarray(
                    self.phy.qam.demodulate_array(
                        phase_locked_data[self.config.pll_preamble_length :]
                    ),
                    dtype=int,
                )
                demodulate_time = time.perf_counter_ns()
                metadata, framed_payload = self.framer.unpack_frame(
                    demodulated_symbols,
                    modulation_order=self.config.modulation_order,
                )
                if metadata is None:
                    logger.warning(
                        "Failed to extract RX metadata header; dropping frame "
                        "(likely too many bit errors)"
                    )
                    continue

                logger.info(
                    f"Times: Matched filtering: {(matched_filter_time - start_time) * 10e-6:.3f} ms, "
                    + f"CFO: {(coarse_frequency_time - matched_filter_time) * 10e-6:.3f} ms, "
                    + f"TED: {(timing_recovery_time - coarse_frequency_time) * 10e-6:.3f} ms, "
                    + f"CORR: {(correlation_time - timing_recovery_time) * 10e-6:.3f} ms, "
                    + f"CODE: {(detect_codeword_time - correlation_time) * 10e-6:.3f} ms, "
                    + f"RM CODE: {(remove_codeword_time - detect_codeword_time) * 10e-6:.3f} ms, "
                    + f"AGC: {(agc_time - remove_codeword_time) * 10e-6:.3f} ms, "
                    + f"PLL: {(phase_locked_loop_time - agc_time) * 10e-6:.3f} ms, "
                    + f"DEMOD: {(demodulate_time - phase_locked_loop_time) * 10e-6:.3f} ms"
                )

            except Exception as exc:
                logger.exception(f"Failed while processing Rx data: {exc}")
                continue

            try:
                self.gui_queue.put_nowait(
                    {
                        "type": "rx_update",
                        "correlation": correlation[start_of_data_index:],
                        "matched_filtered_data": matched_filtered_data[
                            self.config.pll_preamble_length :
                        ],
                        "phase_locked_data": phase_locked_data[
                            self.config.pll_preamble_length :
                        ],
                        "rx_metadata": metadata,
                        "rx_payload": framed_payload,
                        # "decoded_data": decoded_data,
                    }
                )
            except Full:
                logger.warning("Dropping RX GUI frame")
                pass
