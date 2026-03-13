"""TX worker — loads the cyclic TX buffer on the Pluto and loops indefinitely.

The frame is passed in via *tx_queue* as a complex64 ndarray.  After the first
frame is loaded into the cyclic buffer the Pluto DMA handles retransmission
autonomously.  The worker then blocks on the queue waiting for:
  - a new ndarray  → swap the cyclic buffer for the new frame
  - None sentinel  → clean shutdown

Design notes
------------
* Do NOT pass adi.Pluto across process boundaries — create it here.
* tx_cyclic_buffer=True means sdr.tx(frame) arms the DMA loop once; the
  hardware repeats the buffer without any further CPU involvement.
* The worker must call sdr.tx_destroy_buffer() before loading a new frame,
  otherwise pyadi-iio raises a "buffer already created" error.
"""

from __future__ import annotations

import multiprocessing as mp

import adi
import numpy as np
from config import RadioConfig
from utils.log import configure_logging, get_logger  # type: ignore[import]


def tx_worker(config: RadioConfig, tx_queue: mp.Queue) -> None:  # type: ignore[type-arg]
    configure_logging(config.log_level, "tx")
    log = get_logger(__name__)

    log.info("Connecting to TX Pluto at %s …", config.tx_uri)
    sdr: adi.Pluto = adi.Pluto(config.tx_uri)

    # Configure TX RF parameters
    sdr.tx_lo = config.tx_lo_hz
    sdr.sample_rate = config.sample_rate_hz
    sdr.tx_rf_bandwidth = config.tx_rf_bandwidth_hz
    sdr.tx_hardwaregain_chan0 = config.tx_hardware_gain_db
    sdr.tx_cyclic_buffer = config.tx_cyclic_buffer

    log.info(
        "TX configured — LO %.3f MHz, SR %.3f Msps, gain %d dB, cyclic=%s",
        config.tx_lo_hz / 1e6,
        config.sample_rate_hz / 1e6,
        config.tx_hardware_gain_db,
        config.tx_cyclic_buffer,
    )

    cyclic_running = False

    while True:
        try:
            frame = tx_queue.get(timeout=0.1)
        except Exception:
            # Queue.Empty — keep looping if cyclic buffer already running
            continue

        if frame is None:
            log.info("Received shutdown sentinel — stopping TX.")
            break

        if not isinstance(frame, np.ndarray):
            log.warning("tx_queue received unexpected type %s; ignoring.", type(frame))
            continue

        if cyclic_running:
            # Must destroy the old cyclic buffer before starting a new one
            try:
                sdr.tx_destroy_buffer()
            except Exception as exc:
                log.warning("tx_destroy_buffer() raised %s; continuing.", exc)

        log.info("Loading TX frame (%d samples) into cyclic buffer …", len(frame))
        sdr.tx(frame)
        cyclic_running = True
        log.info("TX cyclic buffer armed.")

    # Cleanup
    if cyclic_running:
        try:
            sdr.tx_destroy_buffer()
        except Exception:
            pass
    log.info("TX worker exiting.")
