"""Physical layer RX functionality.

This module provides RX modem functionality including matched filtering,
correlation-based sync detection, downsampling, and carrier recovery (PLL).
"""

import logging
from dataclasses import dataclass

import fir_filter
import modem
import numpy as np
from scipy import signal

from radiolab.config.config import PhyConfig

logger = logging.getLogger(__name__)


@dataclass
class PLLState:
    """State for Phase-Locked Loop carrier recovery."""

    theta: float = 0.0  # Phase estimate
    integrator: float = 0.0  # Integrator state


class ModemRx:
    """RX modem for demodulation and signal processing.

    This class handles:
    - Matched filtering
    - Frame synchronization (correlation-based)
    - Downsampling
    - Phase-locked loop (PLL) for carrier recovery
    - Symbol demodulation
    """

    def __init__(self, config: PhyConfig) -> None:
        """Initialize RX modem.

        Args:
            config: Physical layer configuration
        """
        self.config = config
        self.qam = modem.Qam(config.modulation_order)
        self.qpsk = modem.Qam(4)  # For PLL preamble
        self.sps = config.samples_per_symbol

        # Initialize RRC filter
        rrc = fir_filter.RootRaisedCosine(
            config.rrc_rolloff, config.rrc_span, config.samples_per_symbol
        )
        self.rrc_coeff = np.array(rrc.get_coefficients())
        self.filter_state = signal.lfiltic(self.rrc_coeff, 1, 0)

        # PLL state
        self.pll_state = PLLState()
        self.pll_kp = config.pll_kp
        self.pll_ki = config.pll_ki

        # For plotting/debugging
        self.last_pll_error = None
        self.last_pll_theta = None

        logger.info(
            f"RX Modem initialized - {config.modulation_order}-QAM, "
            f"SPS={config.samples_per_symbol}, RRC β={config.rrc_rolloff}"
        )

    def matched_filter(self, samples: np.ndarray) -> np.ndarray:
        """Apply matched (RRC) filtering to received samples.

        Args:
            samples: Raw IQ samples from radio

        Returns:
            Matched filtered samples
        """
        filtered, self.filter_state = signal.lfilter(
            self.rrc_coeff, 1, samples, zi=self.filter_state
        )
        return filtered

    def detect_frame_start(
        self, samples: np.ndarray, template: np.ndarray
    ) -> tuple[np.intp, np.ndarray]:
        """Detect frame start using correlation with template.

        Args:
            samples: Matched filtered samples
            template: Expected sync pattern (codeword)

        Returns:
            Tuple of (frame_start_index, correlation_result)
        """
        # Normalize samples
        samples_norm = samples / (np.max(np.abs(samples)) + 1e-10)

        # Correlate with template
        correlation = np.correlate(samples_norm, template, mode="same")
        correlation_power = np.abs(correlation) ** 2

        # Find peak
        frame_start = np.argmax(correlation_power)

        return frame_start, correlation_power

    def downsample(self, samples: np.ndarray, offset: int = 0) -> np.ndarray:
        """Downsample to symbol rate.

        Args:
            samples: Upsampled filtered samples
            offset: Sample offset for timing alignment

        Returns:
            Downsampled symbols
        """
        return samples[offset :: self.sps]

    def phase_locked_loop(
        self, symbols: np.ndarray, preamble: np.ndarray | None = None
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Apply phase-locked loop for carrier recovery.

        Args:
            symbols: Input symbols (downsampled)
            preamble: Known preamble for training (if None, uses decision-directed)

        Returns:
            Tuple of (phase_corrected_symbols, pll_error, pll_theta)
        """
        pll_preamble_length = len(preamble) if preamble is not None else 0

        phase_corrected = np.zeros_like(symbols)
        error = np.zeros(len(symbols))
        theta = np.zeros(len(symbols))

        self.reset_pll()

        for i, symbol in enumerate(symbols):
            # Phase correction
            corrected = symbol * np.exp(-1j * self.pll_state.theta)
            phase_corrected[i] = corrected

            # Phase detector
            if preamble is not None and i < pll_preamble_length:
                # Use known preamble for training
                closest_symbol = preamble[i]
            else:
                # Decision-directed mode
                closest_symbol = self.qam.modulate(self.qam.demodulate(corrected))

            # Phase error
            error[i] = np.angle(corrected * np.conj(closest_symbol))

            # Loop filter (PI controller)
            self.pll_state.integrator += self.pll_ki * error[i]
            self.pll_state.theta += self.pll_state.integrator + self.pll_kp * error[i]
            theta[i] = self.pll_state.theta

        # Store for debugging/plotting
        self.last_pll_error = error
        self.last_pll_theta = theta

        return phase_corrected, error, theta

    def demodulate(self, symbols: np.ndarray) -> np.ndarray:
        """Demodulate symbols to bit values.

        Args:
            symbols: Complex constellation symbols

        Returns:
            Integer symbols (0 to M-1)
        """
        demodulated = np.zeros(len(symbols), dtype=int)
        for idx, symbol in enumerate(symbols):
            demodulated[idx] = self.qam.demodulate(symbol)
        return demodulated

    def reset_pll(self) -> None:
        """Reset PLL state (useful between frames)."""
        self.pll_state = PLLState()
