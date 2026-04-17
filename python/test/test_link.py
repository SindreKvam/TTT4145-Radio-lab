"""Pytest module to test the link layer"""

import logging

import numpy as np
import pytest

from radiolab.link.framer import Framer

logger = logging.getLogger(__name__)


@pytest.mark.parametrize("modulation_order", [4, 8, 16])
def test_framer(modulation_order: int):
    framer = Framer()

    payload = np.array([0xD, 0xE, 0xA, 0xD, 0xB, 0xA, 0xB, 0xE])
    metadata = {"img_width": 4, "img_height": 2, "channels": 1}

    data = framer.pack_frame(
        payload,
        metadata=metadata,
        modulation_order=modulation_order,
        frame_counter=0xBADE,
    )

    unpacked_metadata, unpacked_data = framer.unpack_frame(data, modulation_order)

    logger.info(unpacked_metadata)
    logger.info(unpacked_data)

    unpacked_metadata == metadata
    unpacked_data = data
