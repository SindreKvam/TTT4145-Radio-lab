import argparse
import logging
import multiprocessing as mp
import queue

from pipeline.dsp_worker import dsp_worker
from pipeline.rx_worker import rx_worker
from pipeline.tx_worker import tx_worker
from radio import connect_and_configure_pluto

logger = logging.getLogger(__name__)


def main(**kwargs):
    rx_queue = queue.Queue()
    tx_queue = queue.Queue()
    gui_queue = queue.Queue()

    sdr = connect_and_configure_pluto(**kwargs)

    processes = []
    tx_process = mp.Process(target=tx_worker, args=(sdr, tx_queue))
    rx_process = mp.Process(target=rx_worker, args=(sdr, rx_queue))
    sdr_process = mp.Process(target=dsp_worker, args=(rx_queue))

    processes = [tx_process, rx_process]
    for p in processes:
        p.start()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    # parser.add_argument("mode", help="Select mode, rx or tx")
    parser.add_argument(
        "--tx-lo",
        default=2_000_000_000,
        type=int,
        help="The local oscillator frequency of the transmitter",
    )
    parser.add_argument(
        "--rx-lo",
        default=2_000_000_000,
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
