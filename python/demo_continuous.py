#!/usr/bin/env python3
"""Continuous TX/RX demo with live visualization.

This is the main entry point for the continuous transmission/reception demo.
It spawns two processes:
1. TXRX Pipeline: Full-duplex TX/RX operation with DSP processing
2. GUI: Live dashboard displaying all data

Usage:
    python demo_continuous.py [--config config.toml]
"""

import argparse
import logging
import multiprocessing as mp
import signal
from pathlib import Path

from radiolab.config.config import Config
from radiolab.pipeline.gui_process import gui_process
from radiolab.pipeline.txrx_pipeline import txrx_pipeline_process

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for continuous demo."""
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Radiolab Continuous TX/RX Demo",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).parent / "config.toml",
        help="Path to configuration file",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load configuration
    logger.info(f"Loading configuration from {args.config}")
    if args.config.exists():
        config = Config.from_toml(args.config)
    else:
        logger.warning("Config file not found, using defaults")
        config = Config.default()

    logger.info("Configuration loaded")
    logger.info(f"  Modulation: {config.phy.modulation_order}-QAM")
    logger.info(f"  SPS: {config.phy.samples_per_symbol}")
    logger.info(f"  RX LO: {config.radio.rx_lo / 1e6:.1f} MHz")
    logger.info(f"  TX LO: {config.radio.tx_lo / 1e6:.1f} MHz")

    # Create shared resources
    gui_queue = mp.Queue(maxsize=config.gui.queue_maxsize)
    stop_event = mp.Event()

    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        logger.info("Shutdown signal received...")
        stop_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create processes
    processes = []

    txrx_proc = mp.Process(
        target=txrx_pipeline_process,
        args=(config, gui_queue, stop_event),
        name="TxRxPipeline",
        daemon=False,
    )
    processes.append(txrx_proc)

    gui_proc = mp.Process(
        target=gui_process,
        args=(config, gui_queue, stop_event),
        name="GuiDashboard",
        daemon=False,
    )
    processes.append(gui_proc)

    # Start all processes
    logger.info("Starting processes...")
    for proc in processes:
        proc.start()
        logger.info(f"  {proc.name} started (PID: {proc.pid})")

    logger.info("All processes started. Press Ctrl+C to stop.")

    # Wait for processes to finish
    try:
        for proc in processes:
            proc.join()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        # Ensure clean shutdown
        logger.info("Shutting down...")
        stop_event.set()

        # Give processes time to shutdown gracefully
        for proc in processes:
            proc.join(timeout=2)
            if proc.is_alive():
                logger.warning(f"Terminating {proc.name}")
                proc.terminate()
                proc.join(timeout=1)
                if proc.is_alive():
                    logger.warning(f"Killing {proc.name}")
                    proc.kill()

        logger.info("Shutdown complete")


if __name__ == "__main__":
    # Required for multiprocessing on Windows/macOS
    mp.set_start_method("spawn", force=True)
    main()
