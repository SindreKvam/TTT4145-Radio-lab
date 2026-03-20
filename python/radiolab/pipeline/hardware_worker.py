import logging
from queue import Empty, Full, Queue

# from multiprocessing import Event, Process
from threading import Event, Thread

import adi

from radiolab.config.config import PhyConfig

logger = logging.getLogger(__name__)


class HardwareWorker(Thread):
    def __init__(
        self,
        radio: adi.Pluto,
        tx_queue: Queue,
        rx_queue: Queue,
        stop_event: Event,
        config: PhyConfig,
        name: str = "RxTxWorker",
    ):
        logger.info(f"{name} starting")

        super().__init__(name=name, daemon=True)
        self.radio = radio
        self.tx_queue = tx_queue
        self.rx_queue = rx_queue
        self.stop_event = stop_event

        self.config = config

    def run(self) -> None:
        """"""

        # TODO: Configure Adalm Pluto

        while not self.stop_event.is_set():
            rx_data = self.radio.rx()

            # Put receive data in the Rx queue
            try:
                self.rx_queue.put_nowait(rx_data)
            except Full:
                logger.warning("RX buffer full, dropping package")
                self.rx_queue.get()
                self.rx_queue.put_nowait(rx_data)

            # Transmit whatever is in the Tx queue
            try:
                tx_data = self.tx_queue.get_nowait()
                self.radio.tx(tx_data)
            except Empty:
                # logger.warning("TX buffer empty, missed data transfer")
                pass
