"""RX worker — captures IQ samples from the Pluto and passes them to the DSP
worker via shared memory without copying the buffer data.

Zero-copy IPC pattern
---------------------
main.py pre-allocates *ring_slots* SharedMemory blocks and puts all their
names into *free_queue*.

Loop:
  1. Block on free_queue to get a slot name.
  2. Open the shared memory block by name (attach, do not create).
  3. Wrap it as a numpy complex64 view — zero copy.
  4. Call sdr.rx() directly into that view.
  5. Put the slot name into filled_queue for the DSP worker to consume.
  6. Repeat.

The DSP worker is responsible for returning slot names to free_queue after it
has finished reading each slot.

Single-radio mode
-----------------
When config.single_radio_mode is True, this worker also owns the TX side.
Pass tx_frame (a complex64 ndarray) and it will be loaded into the cyclic
buffer before the RX loop starts.  tx_worker is NOT spawned in this mode.

Design notes
------------
* Do NOT pass adi.Pluto across process boundaries — create it here.
* rx_buffer_size on the Pluto must equal n_samples before the first call to
  sdr.rx().  We set it once here from the n_samples argument.
* The worker exits cleanly on KeyboardInterrupt (sent by main.py via SIGTERM
  to the daemon process).
"""

from __future__ import annotations

import multiprocessing as mp
from multiprocessing import resource_tracker
from multiprocessing.shared_memory import SharedMemory

import adi
import numpy as np

from config import RadioConfig
from utils.log import configure_logging, get_logger  # type: ignore[import]


def _attach_shm(name: str) -> SharedMemory:
    """Attach to an existing shared-memory block without registering it with
    the resource tracker.  main.py owns the lifetime; workers are guests."""
    shm = SharedMemory(name=name, create=False)
    # Unregister so the resource tracker in this process does not try to
    # unlink the block on exit (main.py calls unlink()).
    resource_tracker.unregister(shm._name, "shared_memory")  # type: ignore[attr-defined]
    return shm


_COMPLEX64_BYTES = 8


def rx_worker(
    config: RadioConfig,
    free_queue: mp.Queue,  # type: ignore[type-arg]
    filled_queue: mp.Queue,  # type: ignore[type-arg]
    n_samples: int,
    tx_frame: np.ndarray | None = None,
) -> None:
    configure_logging(config.log_level, "rx")
    log = get_logger(__name__)

    log.info("Connecting to Pluto at %s …", config.rx_uri)
    sdr: adi.Pluto = adi.Pluto(config.rx_uri)

    # ---- TX side (single-radio mode only) ------------------------------------
    if tx_frame is not None:
        log.info(
            "Single-radio mode — arming TX cyclic buffer (%d samples) …", len(tx_frame)
        )
        sdr.tx_lo = config.tx_lo_hz
        sdr.tx_rf_bandwidth = config.tx_rf_bandwidth_hz
        sdr.tx_hardwaregain_chan0 = config.tx_hardware_gain_db
        sdr.tx_cyclic_buffer = True
        sdr.tx(tx_frame)
        log.info("TX cyclic buffer armed.")

    # ---- RX side -------------------------------------------------------------
    sdr.rx_lo = config.rx_lo_hz
    sdr.sample_rate = config.sample_rate_hz
    sdr.rx_rf_bandwidth = config.rx_rf_bandwidth_hz
    sdr.gain_control_mode_chan0 = "manual"
    sdr.rx_hardwaregain_chan0 = config.rx_hardware_gain_db
    sdr.rx_buffer_size = n_samples

    # Optional baseband / RF tracking settings
    phy = sdr.ctx.find_device("ad9361-phy")
    rx0 = phy.find_channel("voltage0", False)
    rx0.attrs["quadrature_tracking_en"].value = (
        "1" if config.quadrature_tracking else "0"
    )
    rx0.attrs["rf_dc_offset_tracking_en"].value = (
        "1" if config.rf_dc_offset_tracking else "0"
    )
    rx0.attrs["bb_dc_offset_tracking_en"].value = (
        "1" if config.bb_dc_offset_tracking else "0"
    )

    log.info(
        "RX configured — LO %.3f MHz, SR %.3f Msps, gain %d dB, buffer %d samples",
        config.rx_lo_hz / 1e6,
        config.sample_rate_hz / 1e6,
        config.rx_hardware_gain_db,
        n_samples,
    )

    buf_counter = 0

    while True:
        # 1. Grab a free shared-memory slot
        shm_name: str = free_queue.get()

        # 2. Attach (do not create — main.py already created it)
        shm = _attach_shm(shm_name)

        # 3. View as complex64 — this is a zero-copy numpy array
        buf = np.frombuffer(shm.buf, dtype=np.complex64, count=n_samples)

        # 4. Receive directly into the shared buffer
        raw = sdr.rx()  # returns complex int16-based samples as complex128
        # pyadi-iio returns numpy complex128 by default; downcast to complex64
        buf[:] = raw.astype(np.complex64)

        # Release the numpy view before closing — shm.close() raises
        # BufferError if any exported pointer (ndarray referencing shm.buf)
        # still exists.
        del buf

        # 5. Detach (do not unlink — main.py owns lifetime)
        shm.close()

        # 6. Hand off the name to DSP
        filled_queue.put(shm_name)

        buf_counter += 1
        if buf_counter % 100 == 0:
            log.debug("RX: %d buffers captured", buf_counter)
