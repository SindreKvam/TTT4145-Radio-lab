"""This module contains the framer for the data packages"""

import numpy as np


class Framer:
    def __init__(self) -> None:
        pass

    # TODO: implement framer, images should not need to be coded
    # but it is important that metadata is correct.
    # (image size (widht, height) etc.)

    def flatten_image(self, image: np.ndarray):
        """Return a 1D array of the original image"""

        return np.ravel(image).astype(int)

    def add_metadata(self, payload: np.ndarray, metadata: np.ndarray):
        """"""
        raise NotImplementedError
