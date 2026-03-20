import argparse
import logging
import multiprocessing as mp
import queue
from threading import Event

from pipeline.gui_worker import GuiWorker
from pipeline.hardware_worker import HardwareWorker
from pipeline.rx_worker import RxWorker
from pipeline.tx_worker import TxWorker
from radio import connect_and_configure_pluto

from radiolab.config.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main(**kwargs):
    rx_queue = queue.Queue(maxsize=10)
    tx_queue = queue.Queue(maxsize=10)
    gui_queue = mp.Queue(maxsize=8)

    sdr = connect_and_configure_pluto(**kwargs)

    config = Config.default()
    stop_event = Event()

    processes = []
    processes.append(HardwareWorker(sdr, tx_queue, rx_queue, stop_event, config.phy))
    processes.append(TxWorker(tx_queue, gui_queue, config.phy, stop_event))
    processes.append(
        RxWorker(
            rx_queue,
            gui_queue,
            config.phy,
            stop_event,
            config.radio.time_to_fill_buffer,
        )
    )
    processes.append(GuiWorker(gui_queue, config, stop_event))

    for p in processes:
        p.start()

    for p in processes:
        p.join()


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
