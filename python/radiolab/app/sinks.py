import logging

import numpy as np

logger = logging.getLogger(__name__)


class ImageSink:
    def decode_image(
        self, metadata: dict | None, payload_symbols: np.ndarray
    ) -> np.ndarray | None:
        if metadata is None:
            return None

        width = int(metadata.get("img_width", 0))
        height = int(metadata.get("img_height", 0))
        channels = int(metadata.get("channels", 3))

        if width <= 0 or height <= 0:
            return None
        if channels not in (1, 3):
            return None

        expected_len = width * height * channels
        if len(payload_symbols) < expected_len:
            return None

        try:
            image_symbols = np.asarray(payload_symbols[:expected_len], dtype=int)
            image = np.transpose(
                image_symbols.reshape((height, width, channels)),
                (1, 0, 2),
            )
            return image
        except Exception as exc:
            logger.debug(f"Failed to decode image payload: {exc}")
            return None
