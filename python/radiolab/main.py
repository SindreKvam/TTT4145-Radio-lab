import argparse
import logging
import queue

from radio import connect_and_configure_pluto

logger = logging.getLogger(__name__)


def main(**kwargs):
    rx_queue = queue.Queue()
    tx_queue = queue.Queue()

    print(kwargs)

    sdr = connect_and_configure_pluto(**kwargs)


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
