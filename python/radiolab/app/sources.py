from abc import ABC, abstractmethod
from pathlib import Path

import cv2
import numpy as np

image_path = Path(__file__).parent / "IMG_4399.JPG"


def image_to_m_bit(image_path: str, M: int = 4, scale=0.1):
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

    width = int(img.shape[1] * scale)
    height = int(img.shape[0] * scale)
    resized = cv2.resize(img, (width, height), interpolation=cv2.INTER_AREA)

    return resized // (256 / M), width, height


def array_image_to_m_bit(img: np.ndarray, M: int = 4, scale=1.0):
    width = int(img.shape[1] * scale)
    height = int(img.shape[0] * scale)
    resized = cv2.resize(img, (width, height), interpolation=cv2.INTER_AREA)

    return resized // (256 / M), width, height


class Source(ABC):
    @abstractmethod
    def read(self) -> np.ndarray:
        pass


class ImageSource(Source):
    def __init__(self, image_path: str):
        with open(image_path, "rb") as f:
            self.data = f.read()

    def read(self):
        return self.data


class CameraSource(Source):
    def __init__(
        self, capture_width: int | None = None, capture_height: int | None = None
    ) -> None:
        self.camera = cv2.VideoCapture(0)
        if capture_width is not None and capture_width > 0:
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, int(capture_width))
        if capture_height is not None and capture_height > 0:
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, int(capture_height))

    def read(
        self, num_bits: int = 4, image_scale: float = 0.2
    ) -> tuple[np.ndarray, int, int]:
        """Take image with web-camera and return a scaled image"""

        ret, img = self.camera.read()
        if not ret or img is None:
            raise RuntimeError("Failed to capture image from camera")
        rgb_image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        return array_image_to_m_bit(rgb_image, num_bits, scale=image_scale)
