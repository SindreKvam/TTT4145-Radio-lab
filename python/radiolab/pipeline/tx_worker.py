import logging
from dataclasses import dataclass
from queue import Empty, Queue
from threading import Event, Thread

import adi
import numpy as np

from radiolab.phy.tx import ModemTx

logger = logging.getLogger(__name__)


@dataclass
class TxJob:
    payload: np.ndarray
    tag: str = "untagged"
    repeat: int = 1


class TxWorker(Thread):
    def __init__(
        self,
        radio: adi.Pluto,
        tx_queue: Queue,
        phy: ModemTx,
        stop_event: Event,
        idle_sleep_s: float = 0.01,
        name: str = "TxWorker",
    ):
        """"""
        super().__init__(name=name, daemon=True)
        self.radio = radio
        self.tx_queue = tx_queue
        self.phy = phy
        self.stop_event = stop_event
        self.idle_sleep_s = idle_sleep_s

    def run(self) -> None:
        while not self.stop_event.is_set():
            try:
                job: TxJob = self.tx_queue.get(timeout=self.idle_sleep_s)
            except Empty:
                continue

            try:
                self._handle_job(job)
            except Exception as exc:
                logger.warning(f"[{self.name}] Error handling job {job.tag}: {exc}")
            finally:
                self.tx_queue.task_done()

    def _handle_job(self, job: TxJob) -> None:
        """Do the actual work of transmitting data"""
        for i in range(job.repeat):
            data = job.payload

            data = self.phy.add_codeword(data)
            data = self.phy.modulate_payload(data)
            data = self.phy.add_pll_preamble(data)
            data = self.phy.upsample(data)

            self.radio.tx(data)
