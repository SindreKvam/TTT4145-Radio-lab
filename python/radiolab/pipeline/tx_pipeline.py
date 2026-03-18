"""TX pipeline process for continuous transmission."""

import logging
import multiprocessing as mp
import time
from pathlib import Path

import numpy as np

from radiolab.app.sources import image_path, image_to_m_bit
from radiolab.config.config import Config
from radiolab.phy.tx import ModemTx
from radiolab.radio.pluto import PlutoRadio

logger = logging.getLogger(__name__)


def tx_pipeline_process(
    config: Config,
    gui_queue: mp.Queue,
    stop_event: mp.Event,
):
    """TX pipeline process - continuously transmits data.

    Args:
        config: System configuration
        gui_queue: Queue for sending data to GUI
        stop_event: Event to signal shutdown
    """
    logger.info("TX Pipeline starting...")

    try:
        # Initialize components
        tx_modem = ModemTx(config.phy)
        radio = PlutoRadio(config.radio.uri)

        # Prepare image data
        img_path = config.app.image_path if config.app.image_path else image_path
        m_bit_image, img_width, img_height = image_to_m_bit(
            str(img_path), config.phy.modulation_order, scale=config.app.image_scale
        )
        payload = m_bit_image.flatten().astype(int)

        logger.info(
            f"TX: Image loaded - {img_width}x{img_height}, {len(payload)} symbols"
        )

        # Build complete frame
        tx_samples = tx_modem.build_frame(payload)
        num_symbols = (
            len(tx_modem.get_nasa_codeword())
            + len(tx_modem.get_pll_preamble())
            + len(payload)
        )

        # Configure radio
        buffer_size = len(tx_samples)
        radio.configure(config.radio, buffer_size)

        logger.info(f"TX: Frame built - {len(tx_samples)} samples, cyclic mode enabled")
        logger.info("TX Pipeline ready")

        # Transmit once (cyclic buffer will repeat)
        radio.transmit(tx_samples)
        logger.info("TX: Initial transmission sent (cyclic mode active)")

        # Send metadata to GUI
        try:
            gui_queue.put_nowait(
                {
                    "type": "tx_info",
                    "num_symbols": num_symbols,
                    "num_samples": len(tx_samples),
                    "image_shape": (img_height, img_width),
                    "payload": payload,
                }
            )
            # Send TX samples for plotting (first 2000 samples)
            gui_queue.put_nowait(
                {
                    "type": "tx_samples",
                    "samples": tx_samples[:2000],
                    "timestamp": time.time(),
                }
            )
        except:
            pass  # GUI queue full, skip

        # Keep process alive
        while not stop_event.is_set():
            time.sleep(0.1)

    except Exception as e:
        logger.error(f"TX Pipeline error: {e}", exc_info=True)
    finally:
        if "radio" in locals():
            radio.close()
        logger.info("TX Pipeline stopped")
