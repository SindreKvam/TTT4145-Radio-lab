import queue


def dsp_worker(data_queue: queue.Queue):
    """This worker should do all digital signal processing
    on incomming data from the adalm pluto"""

    while True:
        data = data_queue.get(block=True)
