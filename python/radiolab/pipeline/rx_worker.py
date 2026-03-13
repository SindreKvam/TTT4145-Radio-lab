import queue

import adi


def rx_worker(
    sdr: adi.Pluto,
    rx_queue: queue.Queue,
    max_timeout: None | float = None,
):
    """Receive data from the adalm pluto and put it in the RX queue"""

    while True:
        rx_queue.put(sdr.rx(), block=True, timeout=max_timeout)
