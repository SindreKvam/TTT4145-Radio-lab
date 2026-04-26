import logging
import signal
import time
from multiprocessing import Event, Process
from multiprocessing.queues import Empty, Full, Queue
from threading import Event as ThreadEvent

# from queue import Empty, Full, Queue
from threading import Thread

import adi

from radiolab.config.config import RadioConfig

logger = logging.getLogger(__name__)


class HardwareWorker(Process):
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
        self.radio = None

        self.tx_queue = tx_queue
        self.rx_queue = rx_queue
        self.stop_event = stop_event

        self.config = config

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

        signal.signal(signal.SIGINT, signal.SIG_IGN)

        self.radio = adi.Pluto("usb:")
        self._configure_adalm_pluto()

        self._thread_stop_event = ThreadEvent()

        rx_thread = Thread(target=self._rx_loop, name=f"{self.name}-RX", daemon=True)
        tx_thread = Thread(target=self._tx_loop, name=f"{self.name}-TX", daemon=True)

        rx_thread.start()
        tx_thread.start()

        try:
            while not self.stop_event.is_set():
                time.sleep(0.1)
        finally:
            self._thread_stop_event.set()

            rx_thread.join(timeout=2.0)
            tx_thread.join(timeout=2.0)

            threads_alive = rx_thread.is_alive() or tx_thread.is_alive()
            if threads_alive:
                logger.warning(
                    "Hardware threads still alive during shutdown, skipping radio buffer cleanup"
                )
            else:
                self._cleanup_radio()

    def _rx_loop(self) -> None:
        logger.info("Rx loop started")

        while not self._thread_stop_event.is_set() and not self.stop_event.is_set():
            try:
                rx_data = self.radio.rx()
            except Exception as exc:
                if self._thread_stop_event.is_set() or self.stop_event.is_set():
                    break
                logger.exception(f"RX loop error: {exc}")
                time.sleep(0.05)
                continue

            loop_start_time = time.perf_counter()

            # Put receive data in the Rx queue
            try:
                self.rx_queue.put_nowait(rx_data)
            except Full:
                logger.error("RX buffer full, dropping package")
                # self.rx_queue.get()
                # self.rx_queue.put_nowait(rx_data)

            loop_end_time = time.perf_counter()
            loop_duration = loop_end_time - loop_start_time

            if loop_duration > self.config.time_to_fill_buffer:
                logger.warning(
                    "HardwareWorker Rx loop too slow, "
                    + f"rx is not continuous {loop_duration * 1e3:.2f} ms "
                    + f"> {self.config.time_to_fill_buffer * 1e3:.2f} ms."
                )

    def _tx_loop(self) -> None:
        logger.info("Tx loop started")

        while not self._thread_stop_event.is_set() and not self.stop_event.is_set():
            try:
                tx_data = self.tx_queue.get(timeout=0.001)
                self.radio.tx(tx_data)

            except Empty:
                continue
            except Exception as exc:
                if self._thread_stop_event.is_set() or self.stop_event.is_set():
                    logger.debug(f"Ignoring TX loop error during shutdown: {exc}")
                    break
                logger.exception(f"TX loop error: {exc}")
                time.sleep(0.05)

    def _cleanup_radio(self) -> None:
        if self.radio is None:
            return

        destroy_buffer = getattr(self.radio, "tx_destroy_buffer", None)
        if callable(destroy_buffer):
            try:
                destroy_buffer()
            except Exception as exc:
                exc_text = str(exc)
                exc_errno = getattr(exc, "errno", None)
                if exc_errno == 16 or "errno=16" in exc_text:
                    logger.debug(
                        "TX buffer destroy skipped during shutdown: device busy (errno 16)"
                    )
                else:
                    logger.debug(f"Failed to destroy TX buffer during shutdown: {exc}")

        self.radio = None
