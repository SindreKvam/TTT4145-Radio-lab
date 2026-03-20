import logging
from queue import Empty, Full, Queue

# from multiprocessing import Event, Process
from threading import Event, Thread

import numpy as np
from fir_filter import RootRaisedCosine
from modem import Qam

from radiolab.config.config import PhyConfig
from radiolab.phy.rx import ModemRx

logger = logging.getLogger(__name__)


class RxWorker(Thread):
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

            qam = Qam(self.config.modulation_order)
        except Exception as exc:
            logger.exception(f"Failed to implement Cpp methods: {exc}")

        self.phy = ModemRx(
            qam,
            self.config.samples_per_symbol,
            np.array(rrc.get_coefficients()),
        )

    def run(self) -> None:
        """"""

        while not self.stop_event.is_set():
            try:
                rx_data = self.rx_queue.get(timeout=self.max_timeout)
            except Empty:
                # logger.warning("No Rx data to fetch yet")
                continue

            try:
                matched_filtered_data = self.phy.matched_filtering(rx_data)
                matched_filtered_data = self.phy.recover_timing(matched_filtered_data)

                # try:
                #     start_of_data_index = self.phy.detect_codeword(
                #         matched_filtered_data,
                #         code,
                #         threshold=self.config.codeword_corr_threshold,
                #     )[0]
                # except IndexError:
                #     logger.warning("No data found, dropping received data")
                #     continue
                #
                # matched_filtered_data = self.phy.remove_codeword(
                #     matched_filtered_data,
                #     start_of_data_index,
                #     int(self.config.codeword_length),
                # )

                # Should be AGC
                matched_filtered_data /= np.max(matched_filtered_data)
                phase_locked_data = self.phy.phase_locked_loop(matched_filtered_data)

                logger.info("Data completed")

            except Exception as exc:
                logger.exception(f"Failed while processing Rx data: {exc}")

            try:
                self.gui_queue.put_nowait(
                    {
                        "type": "rx_update",
                        "phase_locked_data": phase_locked_data,
                        "matched_filtered_data": matched_filtered_data,
                    }
                )
            except Full:
                logger.warning("Dropping GUI frame")
                pass
