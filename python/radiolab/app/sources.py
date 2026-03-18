from abc import ABC, abstractmethod
from pathlib import Path

import cv2
import numpy as np


class Source(ABC):
    @abstractmethod
    def read(self) -> np.ndarray:
        pass


image_path = Path(__file__).parent / "IMG_4399.JPG"


def image_to_m_bit(image_path: str, M: int = 4, scale=0.1):
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

    width = int(img.shape[1] * scale)
    height = int(img.shape[0] * scale)
    resized = cv2.resize(img, (width, height), interpolation=cv2.INTER_AREA)

    return resized // (256 / M), width, height


class ImageSource(Source):
    def __init__(self, image_path: str):
        with open(image_path, "rb") as f:
            self.data = f.read()

    def read(self):
        return self.data
