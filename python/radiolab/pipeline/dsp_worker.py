"""DSP worker — full RX processing chain, inline.

Receives IQ buffers from the RX worker via shared memory (zero-copy) and
runs the complete DSP chain:

  1.  Read complex64 samples from a shared-memory slot.
  2.  RRC matched filter (scipy lfilter, causal / streaming state).
  3.  Preamble correlation → find packet start offset.
  4.  Trim NASA PN sync code, downsample by sps.
  5.  Normalise amplitude.
  6.  2nd-order PLL (aided by known QPSK rotation preamble for the first
      *pll_preamble_length* symbols, then decision-directed).
  7.  QAM demodulate the payload symbols.
  8.  Post plot data to plot_queue (non-blocking; drop if GUI is slow).
  9.  Return the shared-memory slot name to free_queue.

DSP chain ported directly from txrx.py.  No phy/ module imports.

Try-block wraps C++ pybind11 modem / fir_filter; falls back gracefully if
the extension is not compiled (import error → NumPy-only path).
"""

from __future__ import annotations

import multiprocessing as mp
from multiprocessing.shared_memory import SharedMemory

import numpy as np
import scipy.signal
from multiprocessing import resource_tracker

from config import RadioConfig
from utils.image import DEFAULT_IMAGE_PATH, image_to_m_bit  # type: ignore[import]
from utils.log import configure_logging, get_logger  # type: ignore[import]


def _attach_shm(name: str) -> SharedMemory:
    """Attach to an existing shared-memory block without registering it with
    the resource tracker.  main.py owns the lifetime; workers are guests."""
    shm = SharedMemory(name=name, create=False)
    resource_tracker.unregister(shm._name, "shared_memory")  # type: ignore[attr-defined]
    return shm


# ---------------------------------------------------------------------------
# DSP library import (C++ pybind11 preferred, NumPy fallback)
# ---------------------------------------------------------------------------
try:
    import fir_filter as _ff
    import modem as _modem

    def _make_modem(order: int):  # type: ignore[return]
        return _modem.Qam(order)

    def _get_rrc_coeffs(beta: float, span: int, sps: int) -> np.ndarray:
        return np.array(_ff.RootRaisedCosine(beta, span, sps).get_coefficients())

    def _demodulate(q, x: complex) -> int:
        return int(q.demodulate(x))

    def _modulate(q, sym: int) -> complex:
        return complex(q.modulate(int(sym)))

    _CPP_AVAILABLE = True

except ImportError:
    _CPP_AVAILABLE = False

    def _rrc_numpy(beta: float, span: int, sps: int) -> np.ndarray:
        """Minimal NumPy RRC approximation (sinc-based)."""
        n = np.arange(-span * sps, span * sps + 1)
        h = np.sinc(n / sps) * np.cos(np.pi * beta * n / sps)
        denom = 1.0 - (2.0 * beta * n / sps) ** 2
        # avoid division by zero at the two special points
        denom = np.where(np.abs(denom) < 1e-9, 1e-9, denom)
        h /= denom
        h /= np.sqrt(np.sum(h**2))
        return h.astype(np.float64)

    class _NumpyQam:
        """Minimal QPSK / QAM demodulator (grey-coded)."""

        _QPSK = np.array([1 + 1j, -1 + 1j, -1 - 1j, 1 - 1j], dtype=complex) / np.sqrt(2)

        def __init__(self, order: int) -> None:
            self.order = order
            if order == 4:
                self._constellation = self._QPSK
            else:
                # Build rectangular M-QAM constellation
                k = int(np.sqrt(order))
                pts = np.arange(-(k - 1), k, 2, dtype=float)
                re, im = np.meshgrid(pts, pts)
                self._constellation = (re + 1j * im).flatten()
                self._constellation /= np.sqrt(
                    np.mean(np.abs(self._constellation) ** 2)
                )

        def demodulate(self, x: complex) -> int:
            dists = np.abs(self._constellation - x)
            return int(np.argmin(dists))

        def modulate(self, sym: int) -> complex:
            return complex(self._constellation[sym])

    def _make_modem(order: int) -> _NumpyQam:
        return _NumpyQam(order)

    def _get_rrc_coeffs(beta: float, span: int, sps: int) -> np.ndarray:
        return _rrc_numpy(beta, span, sps)

    def _demodulate(q: _NumpyQam, x: complex) -> int:
        return q.demodulate(x)

    def _modulate(q: _NumpyQam, sym: int) -> complex:
        return q.modulate(sym)


# ---------------------------------------------------------------------------
# Worker entry point
# ---------------------------------------------------------------------------


def dsp_worker(
    config: RadioConfig,
    free_queue: mp.Queue,  # type: ignore[type-arg]
    filled_queue: mp.Queue,  # type: ignore[type-arg]
    plot_queue: mp.Queue,  # type: ignore[type-arg]
    n_samples: int,
) -> None:
    configure_logging(config.log_level, "dsp")
    log = get_logger(__name__)

    if not _CPP_AVAILABLE:
        log.warning("C++ extensions not available — using NumPy DSP fallbacks.")

    # -----------------------------------------------------------------------
    # Build DSP objects
    # -----------------------------------------------------------------------
    qam = _make_modem(config.qam_order)
    qpsk = _make_modem(4)  # for PLL aided phase detection
    rrc_coeff = _get_rrc_coeffs(config.rrc_beta, config.rrc_span, config.sps)

    # Image dimensions — used to reshape decoded symbols back into a 2-D image.
    # Must match what main.py used when building the TX frame.
    _, img_w, img_h = image_to_m_bit(
        DEFAULT_IMAGE_PATH, qam_order=config.qam_order, scale=0.02
    )
    img_n_symbols = img_w * img_h

    # Streaming filter state (causal, one buffer at a time)
    filter_zi = scipy.signal.lfiltic(rrc_coeff, [1.0], [0.0])

    # NASA PN code modulated symbols (used as correlation template)
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
    modulated_code = np.array(
        [_modulate(qam, int(s)) for s in nasa_symbols], dtype=complex
    )

    # PLL preamble (known QPSK rotation symbols)
    pll_preamble = np.array(
        [1.0 + 1.0j, -1.0 + 1.0j, -1.0 - 1.0j, 1.0 - 1.0j]
        * (config.pll_preamble_length // 4),
        dtype=complex,
    )

    # Pulse-shaped correlation template (same processing as the TX side)
    pulse_shaped_code = np.convolve(modulated_code, rrc_coeff, mode="same")
    mf_code = np.convolve(pulse_shaped_code, rrc_coeff, mode="same")
    oversampled_code = np.zeros(len(mf_code) * config.sps, dtype=complex)
    oversampled_code[:: config.sps] = mf_code

    log.info(
        "DSP ready — %s backend, RRC taps=%d, code_len=%d, pll_preamble=%d",
        "C++" if _CPP_AVAILABLE else "NumPy",
        len(rrc_coeff),
        len(modulated_code),
        config.pll_preamble_length,
    )

    buf_counter = 0

    # PLL state (2nd order)
    pll_theta = 0.0
    pll_integrator = 0.0

    while True:
        # ------------------------------------------------------------------
        # 1. Receive shared-memory slot name from RX worker
        # ------------------------------------------------------------------
        shm_name: str = filled_queue.get()
        shm = _attach_shm(shm_name)
        raw = np.frombuffer(shm.buf, dtype=np.complex64, count=n_samples).copy()
        shm.close()
        # Return slot to RX worker immediately — DSP works on the copy
        free_queue.put(shm_name)

        buf_counter += 1

        # ------------------------------------------------------------------
        # 2. RRC matched filter (streaming state)
        # ------------------------------------------------------------------
        mf_data, filter_zi = scipy.signal.lfilter(rrc_coeff, [1.0], raw, zi=filter_zi)

        # ------------------------------------------------------------------
        # 3. Preamble correlation — find start-of-packet
        # ------------------------------------------------------------------
        mf_norm = mf_data / (np.max(np.abs(mf_data)) + 1e-12)
        corr = np.abs(np.correlate(mf_norm, oversampled_code, mode="same")) ** 2
        sop = int(np.argmax(corr))
        # Shift so the preamble starts at index 0
        mf_data = np.concatenate((mf_data[sop:], mf_data[:sop]))

        # ------------------------------------------------------------------
        # 4. Trim NASA sync code, downsample
        # ------------------------------------------------------------------
        # Remove the half-code-length worth of transient at each boundary
        trim = len(modulated_code) * config.sps // 2
        if 2 * trim >= len(mf_data):
            log.warning("Buffer too short after correlation trim; skipping.")
            continue
        mf_data = mf_data[trim : len(mf_data) - trim]
        mf_data = mf_data[:: config.sps]

        # ------------------------------------------------------------------
        # 5. Normalise
        # ------------------------------------------------------------------
        peak = np.max(np.abs(mf_data))
        if peak < 1e-9:
            log.warning("RX buffer is near-zero after matched filter; skipping.")
            continue
        mf_data = mf_data / peak

        pre_pll = mf_data.copy()  # save for GUI constellation (pre-PLL)

        # ------------------------------------------------------------------
        # 6. 2nd-order PLL
        # ------------------------------------------------------------------
        n_sym = len(mf_data)
        pll_preamble_len = min(config.pll_preamble_length, n_sym)
        e = np.zeros(n_sym)
        theta_trace = np.zeros(n_sym)
        phase_locked = np.zeros(n_sym, dtype=complex)

        for i, x in enumerate(mf_data):
            x_rot = x * np.exp(-1j * pll_theta)
            phase_locked[i] = x_rot

            # Phase detector
            if i < pll_preamble_len:
                ref = pll_preamble[i]
            else:
                ref_sym = _demodulate(qam, x_rot)
                ref = _modulate(qam, ref_sym)

            e[i] = float(np.angle(x_rot * np.conj(ref)))

            # Loop filter (proportional + integral)
            pll_integrator += config.pll_ki * e[i]
            pll_theta += pll_integrator + config.pll_kp * e[i]
            theta_trace[i] = pll_theta

        # ------------------------------------------------------------------
        # 7. Demodulate payload (after PLL preamble)
        # ------------------------------------------------------------------
        payload_syms = phase_locked[pll_preamble_len:]
        decoded = np.array([_demodulate(qam, s) for s in payload_syms], dtype=np.uint8)

        # ------------------------------------------------------------------
        # 7b. Reconstruct RX image from decoded symbols
        # ------------------------------------------------------------------
        rx_image: np.ndarray | None = None
        if len(decoded) >= img_n_symbols:
            rx_pixels = decoded[:img_n_symbols].reshape(img_h, img_w)
            # Map symbols [0, M) back to grayscale [0, 255]
            rx_image = (rx_pixels * (256 // config.qam_order)).astype(np.uint8)

        if buf_counter % 10 == 0:
            log.debug(
                "DSP buf #%d — sop=%d, syms=%d, payload=%d",
                buf_counter,
                sop,
                n_sym,
                len(decoded),
            )

        # ------------------------------------------------------------------
        # 8. Send plot data to GUI (non-blocking — drop if queue is full)
        # ------------------------------------------------------------------
        plot_payload = {
            "pre_pll": pre_pll[pll_preamble_len:],  # constellation pre-PLL
            "post_pll": payload_syms,  # constellation post-PLL
            "pll_error": e,  # PLL error trace
            "decoded": decoded,  # decoded symbols
            "rx_image": rx_image,  # reconstructed image (or None)
        }
        try:
            plot_queue.put_nowait(plot_payload)
        except Exception:
            pass  # GUI lagging behind — drop this frame
