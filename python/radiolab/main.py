import argparse
import logging
import multiprocessing as mp
import time

from pipeline.gui_worker import GuiWorker
from pipeline.hardware_worker import HardwareWorker
from pipeline.rx_worker import RxWorker
from pipeline.tx_worker import TxWorker

from radiolab.config.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main(**kwargs):
    rx_queue = mp.Queue(maxsize=20)
    tx_queue = mp.Queue(maxsize=18)
    gui_queue = mp.Queue(maxsize=8)

    config = Config.default()
    stop_event = mp.Event()

    hardware_worker = HardwareWorker(tx_queue, rx_queue, stop_event, config.radio)
    tx_worker = TxWorker(tx_queue, gui_queue, config.phy, stop_event)
    rx_worker = RxWorker(
        rx_queue,
        gui_queue,
        config.phy,
        stop_event,
        config.radio.time_to_fill_buffer,
    )
    gui_worker = GuiWorker(gui_queue, config, stop_event)

    processes = [hardware_worker, tx_worker, rx_worker, gui_worker]

    for p in processes:
        p.start()

    try:
        while True:
            if not gui_worker.is_alive():
                logger.info("GUI worker exited, requesting shutdown")
                break

            dead_workers = [
                p for p in (hardware_worker, tx_worker, rx_worker) if not p.is_alive()
            ]
            if dead_workers:
                logger.warning(
                    "Worker(s) exited unexpectedly: %s",
                    ", ".join(p.name for p in dead_workers),
                )
                break

            time.sleep(0.2)

    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received, requesting shutdown")

    finally:
        stop_event.set()

        for p in processes:
            p.join(timeout=3.0)

        still_alive = [p for p in processes if p.is_alive()]
        if still_alive:
            logger.warning(
                "Force terminating %d process(es): %s",
                len(still_alive),
                ", ".join(p.name for p in still_alive),
            )
            for p in still_alive:
                p.terminate()
            for p in still_alive:
                p.join(timeout=1.0)

        logger.info("Shutdown complete")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--tx-lo",
        default=2_400_000_000,
        type=int,
        help="The local oscillator frequency of the transmitter",
    )
    parser.add_argument(
        "--rx-lo",
        default=2_400_000_000,
        type=int,
        help="The local oscillator frequency of the receiver",
    )
    parser.add_argument(
        "--modulation",
        "-M",
        default=4,
        type=int,
        help="M-QAM modulation scheme",
    )
    parser.add_argument(
        "--buffer-size",
        default=int(2**12),
        type=int,
        help="Buffer size, given in number of symbols",
    )
    parser.add_argument(
        "--sps",
        default=8,
        help="Number of Samples per Symbol (sps)",
    )
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    kwargs = vars(args)

    main(**kwargs)
