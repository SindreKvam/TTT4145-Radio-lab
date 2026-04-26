import logging

import numpy as np
import pytest

from radiolab.app.sinks import ImageSink
from radiolab.app.sources import ImageSource, image_path

logger = logging.getLogger(__name__)


@pytest.mark.parametrize("image_path", [image_path])
def test_image_source(image_path):
    img_src = ImageSource(image_path)
    img = img_src.read()

    assert isinstance(img, bytes)


def test_image_sink_decodes_raw_payload():
    sink = ImageSink()

    metadata = {"img_width": 3, "img_height": 2, "channels": 1}
    payload = np.array([0, 1, 2, 3, 0, 1], dtype=int)

    image = sink.decode_image(metadata, payload)

    assert image is not None
    assert image.shape == (3, 2, 1)
    assert np.array_equal(image[:, :, 0], np.array([[0, 3], [1, 0], [2, 1]]))
