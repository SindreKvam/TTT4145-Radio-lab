"""RadioLab pipeline supervisor.

Responsibilities:
  1. Parse CLI arguments and build a RadioConfig.
  2. Pre-allocate a pool of SharedMemory blocks for the RX→DSP zero-copy path.
  3. Build the TX frame once (all DSP lives in the main process here so the
     child only needs to start the cyclic buffer).
  4. Spawn tx_worker, rx_worker, dsp_worker, and (optionally) gui_worker.
  5. Join / clean up on KeyboardInterrupt or normal exit.

Two-radio mode: pass --rx-uri and --tx-uri pointing to separate Pluto IPs.
Single-radio mode (default): both URIs point to the same device.
"""

from __future__ import annotations

import argparse
import multiprocessing as mp
import signal
import sys
from multiprocessing.shared_memory import SharedMemory
from typing import Any

import fir_filter
import modem as modem_lib
import numpy as np
from config import RadioConfig
from pipeline.dsp_worker import dsp_worker
from pipeline.gui_worker import gui_worker  # type: ignore[import]
from pipeline.rx_worker import rx_worker
from pipeline.tx_worker import tx_worker
from utils.image import DEFAULT_IMAGE_PATH, image_to_m_bit  # type: ignore[import]
from utils.log import configure_logging, get_logger  # type: ignore[import]

# Number of complex64 samples per shared-memory slot.
# RX worker writes one sdr.rx() buffer per slot.
# Must be set before the pool is allocated; workers derive it from config.
_COMPLEX64_BYTES = 8  # sizeof(complex64)


def _build_tx_frame(
    config: RadioConfig,
) -> tuple[np.ndarray, np.ndarray, int, int]:
    """Construct the pulse-shaped, scaled TX frame ready for sdr.tx().

    All TX DSP runs here in the main process.  The result (a complex64
    ndarray) is put into tx_queue once so tx_worker can start the cyclic
    buffer, then the worker simply waits for a replacement frame or a None
    shutdown sentinel.

    Returns:
        (tx_frame, tx_pixels, img_w, img_h) where tx_pixels is the
        grayscale uint8 2-D image that was transmitted (for display).
    """

    qam = modem_lib.Qam(config.qam_order)
    qpsk = modem_lib.Qam(4)
    rrc = fir_filter.RootRaisedCosine(config.rrc_beta, config.rrc_span, config.sps)
    rrc_coeff = np.array(rrc.get_coefficients())

    def modulate(q, symbol: int) -> complex:
        return q.modulate(int(symbol))

    def _modulate_array(q, arr: np.ndarray) -> np.ndarray:
        out = np.empty(len(arr), dtype=complex)
        for i, v in enumerate(arr):
            out[i] = q.modulate(int(v))
        return out

    # ---------- NASA PN preamble (correlation anchor) -------------------------
    NASA_CODES = {
        32: 0x89445BC1,
        36: 0xC6859AE80,
        64: 0xEC10845E8B3CB0AC,
    }
    code_int = NASA_CODES[config.nasa_code_bits]
    bits_per_sym = config.bits_per_symbol
    total_bits = config.nasa_code_bits
    binary_str = format(code_int, f"0{total_bits}b")
    nasa_symbols = np.array(
        [
            int(binary_str[i : i + bits_per_sym], 2)
            for i in range(0, total_bits, bits_per_sym)
        ],
        dtype=int,
    )
    modulated_code = _modulate_array(qam, nasa_symbols)

    # ---------- PLL rotation preamble -----------------------------------------
    pll_preamble = np.array(
        [1.0 + 1.0j, -1.0 + 1.0j, -1.0 - 1.0j, 1.0 - 1.0j]
        * (config.pll_preamble_length // 4),
        dtype=complex,
    )

    # ---------- Image payload --------------------------------------------------
    symbols_2d, img_w, img_h = image_to_m_bit(
        DEFAULT_IMAGE_PATH, qam_order=config.qam_order, scale=0.02
    )
    payload_symbols = symbols_2d.flatten().astype(int)
    modulated_payload = _modulate_array(qam, payload_symbols)

    # ---------- Assemble frame ------------------------------------------------
    frame_symbols = np.concatenate((modulated_code, pll_preamble, modulated_payload))

    # Oversample
    oversampled = np.zeros(len(frame_symbols) * config.sps, dtype=complex)
    oversampled[:: config.sps] = frame_symbols

    # Pulse-shape
    pulse_shaped = np.convolve(oversampled, rrc_coeff, mode="same")

    # Scale to ADC range and normalise peak to 2^14
    peak = np.max(np.abs(pulse_shaped))
    if peak > 0:
        pulse_shaped = pulse_shaped / peak * (2**14)

    # Convert symbols back to [0, 255] grayscale for display
    tx_pixels = (symbols_2d * (256 // config.qam_order)).astype(np.uint8)

    return pulse_shaped.astype(np.complex64), tx_pixels, img_w, img_h


def _allocate_shm_pool(
    config: RadioConfig, n_samples: int, ctx: Any
) -> tuple[list[SharedMemory], Any, Any]:
    """Allocate a ring of shared-memory slots for the RX→DSP path.

    Returns:
        shm_list   - keep alive in main process (prevents GC / OS cleanup)
        free_queue - names of slots available for the RX worker to write into
        filled_queue - names of slots filled by RX, waiting for DSP to read
    """
    nbytes = n_samples * _COMPLEX64_BYTES
    shm_list: list[SharedMemory] = []
    free_q = ctx.Queue()
    filled_q = ctx.Queue()

    for _ in range(config.ring_slots):
        shm = SharedMemory(create=True, size=nbytes)
        shm_list.append(shm)
        free_q.put(shm.name)

    return shm_list, free_q, filled_q


def main() -> None:
    parser = argparse.ArgumentParser(
        description="RadioLab multiprocessing pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--rx-uri", default="usb:", help="RX Pluto URI")
    parser.add_argument("--tx-uri", default="usb:", help="TX Pluto URI")
    parser.add_argument("--rx-lo", default=2_400_000_000, type=int, help="RX LO (Hz)")
    parser.add_argument("--tx-lo", default=2_400_000_000, type=int, help="TX LO (Hz)")
    parser.add_argument(
        "--sample-rate", default=5_000_000, type=int, help="Sample rate (Hz)"
    )
    parser.add_argument("--qam-order", default=4, type=int, help="QAM order M")
    parser.add_argument("--sps", default=8, type=int, help="Samples per symbol")
    parser.add_argument("--rx-gain", default=30, type=int, help="RX hardware gain (dB)")
    parser.add_argument(
        "--tx-gain", default=-30, type=int, help="TX hardware gain (dB, negative)"
    )
    parser.add_argument(
        "--ring-slots", default=16, type=int, help="Shared memory ring size"
    )
    parser.add_argument("--no-gui", action="store_true", help="Disable GUI")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level",
    )
    args = parser.parse_args()

    configure_logging(args.log_level, "main")
    log = get_logger(__name__)

    config = RadioConfig(
        rx_uri=args.rx_uri,
        tx_uri=args.tx_uri,
        rx_lo_hz=args.rx_lo,
        tx_lo_hz=args.tx_lo,
        sample_rate_hz=args.sample_rate,
        qam_order=args.qam_order,
        sps=args.sps,
        rx_hardware_gain_db=args.rx_gain,
        tx_hardware_gain_db=args.tx_gain,
        ring_slots=args.ring_slots,
        enable_gui=not args.no_gui,
        log_level=args.log_level,
    )

    # ---- spawn context — must be created before any Queue or Process --------
    ctx = mp.get_context("spawn")

    log.info("Building TX frame …")
    tx_frame, tx_pixels, _img_w, _img_h = _build_tx_frame(config)
    log.info(
        "TX frame: %d samples (%.1f ms at %d Msps)",
        len(tx_frame),
        len(tx_frame) / config.sample_rate_hz * 1e3,
        config.sample_rate_hz // 1_000_000,
    )

    # Number of samples per RX buffer (must match what rx_worker will ask for)
    rx_n_samples = config.effective_rx_buffer_size(len(tx_frame) // config.sps)
    log.info("RX buffer: %d samples", rx_n_samples)

    # Shared memory pool for zero-copy RX→DSP
    shm_list, free_q, filled_q = _allocate_shm_pool(config, rx_n_samples, ctx)
    log.info(
        "Allocated %d shared-memory slots × %d bytes",
        config.ring_slots,
        rx_n_samples * _COMPLEX64_BYTES,
    )

    # GUI queue (small packets: plot data)
    plot_queue = ctx.Queue(maxsize=32)

    # TX queue: main → tx_worker (pass initial frame; None = shutdown)
    tx_queue = ctx.Queue(maxsize=4)
    tx_queue.put(tx_frame)  # initial frame

    # ---- spawn workers -------------------------------------------------------

    processes: list[Any] = []

    if config.single_radio_mode:
        # One Pluto for both TX and RX — rx_worker owns the device and arms
        # the cyclic TX buffer itself before starting the RX loop.
        log.info("Single-radio mode: rx_worker will own TX + RX on %s", config.rx_uri)
        p_rx = ctx.Process(
            target=rx_worker,
            args=(config, free_q, filled_q, rx_n_samples, tx_frame),
            name="rx_worker",
            daemon=True,
        )
        processes.append(p_rx)
    else:
        # Two separate Pluto devices — spawn independent TX and RX workers.
        log.info("Two-radio mode: TX on %s, RX on %s", config.tx_uri, config.rx_uri)
        p_tx = ctx.Process(
            target=tx_worker,
            args=(config, tx_queue),
            name="tx_worker",
            daemon=True,
        )
        p_rx = ctx.Process(
            target=rx_worker,
            args=(config, free_q, filled_q, rx_n_samples),
            name="rx_worker",
            daemon=True,
        )
        processes.extend([p_tx, p_rx])

    p_dsp = ctx.Process(
        target=dsp_worker,
        args=(config, free_q, filled_q, plot_queue, rx_n_samples),
        name="dsp_worker",
        daemon=True,
    )
    processes.append(p_dsp)

    if config.enable_gui:
        p_gui = ctx.Process(
            target=gui_worker,
            args=(config, plot_queue),
            name="gui_worker",
            daemon=True,
        )
        processes.append(p_gui)

    log.info("Starting workers: %s", [p.name for p in processes])
    for p in processes:
        p.start()

    # Send the TX image to the GUI once — it is static for the session.
    if config.enable_gui:
        try:
            plot_queue.put_nowait({"tx_image": tx_pixels})
        except Exception:
            pass

    # ---- wait for shutdown ---------------------------------------------------
    def _shutdown(signum, frame):  # noqa: ARG001
        log.info("Received signal %s — shutting down …", signum)
        if not config.single_radio_mode:
            tx_queue.put(None)  # signal tx_worker to stop
        for p in processes:
            p.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        for p in processes:
            p.join()
    except KeyboardInterrupt:
        _shutdown(signal.SIGINT, None)
    finally:
        # Release shared memory
        for shm in shm_list:
            try:
                shm.close()
                shm.unlink()
            except Exception:
                pass
        log.info("Clean exit.")


if __name__ == "__main__":
    main()
