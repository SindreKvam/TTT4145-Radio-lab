import logging
import time

# from queue import Empty, Full, Queue
from multiprocessing import Event, Process
from multiprocessing.queues import Empty, Full, Queue

# from threading import Event, Thread
import numpy as np
from fir_filter import RootRaisedCosine
from modem import Qam

from radiolab.config.config import PhyConfig
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

        try:
            rrc = RootRaisedCosine(
                self.config.rrc_beta,
                self.config.rrc_span,
                self.config.samples_per_symbol,
            )
            rrc_coeff = np.array(rrc.get_coefficients())

            qam = Qam(self.config.modulation_order)
        except Exception as exc:
            logger.exception(f"Failed to implement Cpp methods: {exc}")

        try:
            # Get codeword, and simulate that it has gone through modulation
            # Upsampling, pulse shaping, then down-sampled
            code = _get_codeword(
                self.config.codeword_length, self.config.modulation_order
            )
            modulated_code = np.zeros_like(code, dtype=complex)
            for idx, val in enumerate(code):
                modulated_code[idx] = qam.modulate(val)

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
                    int(self.config.codeword_length),
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

                # Decode
                # decoded_data = np.zeros_like(phase_locked_data, dtype=int)
                # for idx, val in enumerate(phase_locked_data):
                #     # if idx >= :
                #     decoded_data[idx] = self.phy.qam.demodulate(val)

                logger.info(
                    f"Times: {(matched_filter_time - start_time) * 10e-6} ms, "
                    + f"{(timing_recovery_time - matched_filter_time) * 10e-6} ms, "
                    + f"{(correlation_time - timing_recovery_time) * 10e-6} ms, "
                    + f"{(detect_codeword_time - correlation_time) * 10e-6} ms, "
                    + f"{(remove_codeword_time - detect_codeword_time) * 10e-6} ms, "
                    + f"{(agc_time - timing_recovery_time) * 10e-6} ms, "
                    + f"{(phase_locked_loop_time - agc_time) * 10e-6} ms"
                )

            except Exception as exc:
                logger.exception(f"Failed while processing Rx data: {exc}")

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
                        # "decoded_data": decoded_data,
                    }
                )
            except Full:
                logger.warning("Dropping RX GUI frame")
                pass
