import logging
import signal
import time
from dataclasses import dataclass
from enum import StrEnum

# from queue import Full, Queue
from multiprocessing import Event, Process
from multiprocessing.queues import Empty, Full, Queue

# from threading import Event, Thread
import numpy as np
from commpy.filters import rrcosfilter
from modem import Qam

from radiolab.app.sources import CameraSource, image_path, image_to_m_bit
from radiolab.config.config import PhyConfig
from radiolab.link.framer import Framer
from radiolab.link.scrambler import PayloadScrambler
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
    metadata: dict = None
    tag: Tags = Tags.UNTAGGED
    repeat: int = 1


class TxWorker(Process):
    def __init__(
        self,
        tx_queue: Queue,
        gui_queue: Queue,
        control_queue: Queue,
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
        self.control_queue = control_queue
        self.config = config
        self.stop_event = stop_event
        self.idle_sleep_s = idle_sleep_s

        self.camera = None
        self.framer = Framer()
        self.scrambler = PayloadScrambler(
            seed=self.config.scrambler_seed,
            polynomial=self.config.scrambler_polynomial,
            width=self.config.scrambler_width,
            enabled=self.config.scrambler_enabled,
        )
        self.frame_counter = 0
        self.tx_const_preview_len = self.config.tx_constellation_preview_len

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

        self.phy = ModemTx(
            qam,
            self.config.samples_per_symbol,
            rrc_coeff,
        )

    def _generate_image_data_job(self) -> TxJob:
        """Send constant image stream"""

        job = TxJob(payload=None, tag=Tags.IMAGE)

        m_bit_image, img_width, img_height = image_to_m_bit(
            image_path, self.phy.M, scale=self.config.tx_static_image_scale
        )
        job.payload = m_bit_image.flatten().astype(int)
        job.metadata = {"img_width": img_width, "img_height": img_height, "channels": 1}

        return job

    def _generate_camera_data_job(self, image_scale=0.2) -> TxJob:
        """Connect to camera and take image as quickly as possible"""

        if self.camera is None:
            raise RuntimeError("Camera source is not initialized")

        img, img_width, img_height = self.camera.read(
            self.phy.M, image_scale=image_scale
        )
        payload = self.framer.flatten_image(img)

        job = TxJob(
            payload=payload,
            tag=Tags.CAMERA,
            metadata={"img_width": img_width, "img_height": img_height, "channels": 3},
        )

        return job

    def _generate_speech_job(self) -> TxJob:
        """"""

        job = TxJob(payload=None, tag=Tags.SPEECH)
        return job

    def run(self) -> None:
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        try:
            self.camera = CameraSource(
                capture_width=self.config.tx_camera_capture_width,
                capture_height=self.config.tx_camera_capture_height,
            )

            while not self.stop_event.is_set():
                self._drain_control_queue()
                try:
                    job = self._generate_camera_data_job(
                        image_scale=self.config.tx_camera_image_scale
                    )
                except Exception as exc:
                    if self.stop_event.is_set():
                        logger.debug(
                            f"Ignoring TX generate error during shutdown: {exc}"
                        )
                        break
                    logger.exception(f"Error generating job: {exc}")
                    time.sleep(self.idle_sleep_s)
                    continue

                try:
                    self._handle_job(job)
                except Exception as exc:
                    if self.stop_event.is_set():
                        logger.debug(f"Ignoring TX handle error during shutdown: {exc}")
                        break
                    logger.exception(
                        f"[{self.name}] Error handling job {job.tag}: {exc}"
                    )
        except KeyboardInterrupt:
            self.stop_event.set()
        except BaseException as exc:
            if self.stop_event.is_set():
                logger.debug(f"Ignoring TX worker exception during shutdown: {exc}")
            else:
                logger.exception(f"[{self.name}] Unhandled worker exception: {exc}")
        finally:
            if (
                self.camera is not None
                and getattr(self.camera, "camera", None) is not None
            ):
                try:
                    self.camera.camera.release()
                except Exception as exc:
                    logger.debug(f"Failed to release camera during shutdown: {exc}")

    def _handle_job(self, job: TxJob) -> None:
        """Do the actual work of transmitting data"""
        self._drain_control_queue()
        for i in range(job.repeat):
            if self.stop_event.is_set():
                return

            self._drain_control_queue()

            data = img = job.payload

            data = self.scrambler.scramble_symbols(data, self.phy.M)

            data = self.framer.pack_frame(
                data,
                metadata=job.metadata,
                modulation_order=self.phy.M,
                frame_counter=self.frame_counter,
            )

            payload = self.phy.modulate_payload(data)

            data = self.phy.add_pll_preamble(
                payload, preamble_length=self.config.pll_preamble_length
            )
            data = self.phy.add_modulated_codeword(data, self.config.codeword_length)
            data = self.phy.upsample(data)
            data = self.phy.pulse_shape(data)

            data *= 2**14

            try:
                self.tx_queue.put_nowait(data)
            except Full:
                # logger.warning("Tx Queue Full!")
                continue

            try:
                self.gui_queue.put_nowait(
                    {
                        "type": "tx_update",
                        "tx_const_preview": payload[: self.tx_const_preview_len],
                        "metadata": job.metadata,
                        # TODO: Move re-structuring of image to app / link layer
                        "tx_image": np.transpose(
                            np.reshape(
                                img,
                                (
                                    job.metadata["img_height"],
                                    job.metadata["img_width"],
                                    job.metadata.get("channels", 3),
                                ),
                            ),
                            (1, 0, 2),
                        ),
                    }
                )
            except Full:
                logger.warning("GUI Queue full, dropping Tx data frame")
                continue

            # Update frame counter only if frame actually was transmitted
            self.frame_counter = (self.frame_counter + 1) & 0xFFFFFFFF

    def _drain_control_queue(self) -> None:
        while True:
            try:
                msg = self.control_queue.get_nowait()
            except Empty:
                break

            if msg.get("type") != "control":
                continue

            if msg.get("target") == "scrambler_enabled":
                value = msg.get("value")
                if isinstance(value, bool):
                    self.scrambler.enabled = value
