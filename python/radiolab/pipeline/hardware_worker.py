import logging
from queue import Empty, Full, Queue
from threading import Event, Thread

# from multiprocessing import Event, Process
# from multiprocessing.queues import Empty, Full, Queue
import adi

from radiolab.config.config import RadioConfig

logger = logging.getLogger(__name__)


class HardwareWorker(Thread):
    def __init__(
        self,
        tx_queue: Queue,
        rx_queue: Queue,
        stop_event: Event,
        config: RadioConfig,
        name: str = "RxTxWorker",
    ):
        logger.info(f"{name} starting")

        super().__init__(name=name, daemon=True)
        self.radio = adi.Pluto("usb:")

        self.tx_queue = tx_queue
        self.rx_queue = rx_queue
        self.stop_event = stop_event

        self.config = config
        self._configure_adalm_pluto()

    def _configure_adalm_pluto(self) -> None:
        """"""

        # Configure Adalm Pluto
        self.radio.rx_rf_bandwidth = self.config.rx_rf_bandwidth
        self.radio.sample_rate = self.config.sample_rate
        self.radio.rx_buffer_size = self.config.rx_buffer_size
        self.radio.rx_lo = self.config.rx_lo_hz
        self.radio.tx_lo = self.config.tx_lo_hz
        self.radio.tx_cyclic_buffer = self.config.tx_cyclic_buffer
        self.radio.tx_hardwaregain_chan0 = self.config.tx_hardwaregain_chan0
        self.radio.gain_control_mode_chan0 = self.config.gain_control_mode_chan0

        phy = self.radio.ctx.find_device("ad9361-phy")
        rx0 = phy.find_channel("voltage0", False)

        rx0.attrs["quadrature_tracking_en"] = (
            "1" if self.config.quadrature_tracking_en else "0"
        )

    def run(self) -> None:
        """"""

        while not self.stop_event.is_set():
            # start_time = time.perf_counter()
            rx_data = self.radio.rx()
            # receive_time = time.perf_counter()

            # if receive_time - start_time < self.config.time_to_fill_buffer:
            #     logger.warning(
            #         "RX receive took too much time, packet most likely dropped"
            #     )

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
