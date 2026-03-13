"""Image utilities for the RadioLab pipeline.

Converts an image file into a flat array of M-bit integer symbols ready
for QAM modulation.  Wraps the logic that was previously in
image_manipulator.py, using the standard library + numpy + opencv.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

# Default image path — two levels up from this file, at the repo root.
DEFAULT_IMAGE_PATH: Path = Path(__file__).parent.parent.parent.parent / "IMG_4399.JPG"


def image_to_m_bit(
    image_path: Path | str,
    qam_order: int = 4,
    scale: float = 0.02,
) -> tuple[np.ndarray, int, int]:
    """Load a grayscale image, resize it, and quantise to M-bit symbols.

    Args:
        image_path: Path to the image file.
        qam_order:  QAM order M (4, 16, 64, 256).  Each pixel maps to one
                    log2(M)-bit symbol in [0, M).
        scale:      Resize factor applied to both width and height before
                    quantisation.  0.02 gives a very small image suitable
                    for over-the-air testing.

    Returns:
        (symbols, width, height) where *symbols* is a 2-D uint8 ndarray of
        shape (height, width) with values in [0, M), and *width* / *height*
        are the pixel dimensions after resizing.
    """
    img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")

    width = max(1, int(img.shape[1] * scale))
    height = max(1, int(img.shape[0] * scale))
    resized = cv2.resize(img, (width, height), interpolation=cv2.INTER_AREA)

    # Map [0, 255] → [0, M-1]
    symbols = (resized // (256 // qam_order)).astype(np.uint8)
    # Clamp to [0, M-1] in case of rounding edge-cases
    symbols = np.clip(symbols, 0, qam_order - 1)

    return symbols, width, height
