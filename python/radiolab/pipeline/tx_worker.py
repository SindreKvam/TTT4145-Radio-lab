import logging
from dataclasses import dataclass
from enum import StrEnum
from queue import Full, Queue

# from multiprocessing import Event, Process
from threading import Event, Thread

import numpy as np
from fir_filter import RootRaisedCosine
from modem import Qam

from radiolab.app.sources import image_path, image_to_m_bit
from radiolab.config.config import PhyConfig
from radiolab.phy.tx import ModemTx

logger = logging.getLogger(__name__)


class Tags(StrEnum):
    IMAGE = "image"
    CAMERA = "camera"
    SPEECH = "speech"
    UNTAGGED = "untagged"


@dataclass
class TxJob:
    payload: np.ndarray
    tag: Tags = Tags.UNTAGGED
    repeat: int = 1


class TxWorker(Thread):
    def __init__(
        self,
        tx_queue: Queue,
        gui_queue: Queue,
        config: PhyConfig,
        stop_event: Event,
        idle_sleep_s: float = 0.01,
        name: str = "TxWorker",
    ):
        """"""

        logger.info(f"{name} starting")

        super().__init__(name=name, daemon=True)
        self.tx_queue = tx_queue
        self.gui_queue = gui_queue
        self.config = config
        self.stop_event = stop_event
        self.idle_sleep_s = idle_sleep_s

        try:
            rrc = RootRaisedCosine(
                self.config.rrc_beta,
                self.config.rrc_span,
                self.config.samples_per_symbol,
            )

            qam = Qam(self.config.modulation_order)
        except Exception as exc:
            logger.exception(f"Failed to implement Cpp methods: {exc}")

        self.phy = ModemTx(
            qam,
            self.config.samples_per_symbol,
            np.array(rrc.get_coefficients()),
        )

    def _generate_image_data_job(self) -> TxJob:
        """"""

        job = TxJob(payload=None, tag=Tags.IMAGE)

        m_bit_image, img_width, img_height = image_to_m_bit(
            image_path, self.phy.M, scale=0.02
        )
        job.payload = m_bit_image.flatten().astype(int)

        return job

    def _generate_camera_data_job(self) -> TxJob:
        job = TxJob(tag=Tags.CAMERA)

    def _generate_speech_job(self) -> TxJob:
        job = TxJob(tag=Tags.SPEECH)

    def run(self) -> None:
        while not self.stop_event.is_set():
            try:
                job = self._generate_image_data_job()
            except Exception as exc:
                logger.exception(f"Error generating job: {exc}")

            try:
                self._handle_job(job)
            except Exception as exc:
                logger.exception(f"[{self.name}] Error handling job {job.tag}: {exc}")

    def _handle_job(self, job: TxJob) -> None:
        """Do the actual work of transmitting data"""
        for i in range(job.repeat):
            data = job.payload

            data = self.phy.modulate_payload(data)
            data = self.phy.add_pll_preamble(
                data, preamble_length=self.config.pll_preamble_length
            )
            data = self.phy.add_modulated_codeword(data, self.config.codeword_length)
            data = self.phy.upsample(data)
            data = self.phy.pulse_shape(data)

            try:
                self.gui_queue.put_nowait(
                    {
                        "type": "tx_update",
                        "tx_data": data,
                    }
                )
            except Full:
                logger.warning("GUI Queue full, dropping Tx data frame")

            data *= 2**14

            try:
                self.tx_queue.put_nowait(data)
            except Full:
                logger.warning("Tx Queue is not emptied fast enough")
