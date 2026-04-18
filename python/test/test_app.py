import logging

import pytest

from radiolab.app.sources import ImageSource, image_path

logger = logging.getLogger(__name__)


@pytest.mark.parametrize("image_path", [image_path])
def test_image_source(image_path):
    img_src = ImageSource(image_path)
    img = img_src.read()

    assert isinstance(img, bytes)
