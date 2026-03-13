import queue

import adi


def tx_worker(sdr: adi.Pluto, tx_queue: queue.Queue):
    """"""

    while True:
        frame = tx_queue.get(block=True)
        sdr.tx(frame)
