"""Physical layer TX functionality.

This module provides TX modem functionality including modulation,
pulse shaping, upsampling, and preamble generation.
"""

import logging

import fir_filter
import modem
import numpy as np

from radiolab.config.config import PhyConfig

logger = logging.getLogger(__name__)

# NASA codewords with good autocorrelation properties
# Reference: https://ntrs.nasa.gov/api/citations/19800017860/downloads/19800017860.pdf
NASA_CODEWORDS: dict[int, int] = {
    32: 0x89445BC1,
    36: 0xC6859AE80,
    64: 0xEC10845E8B3CB0AC,
}


def int_to_m_bit_chunks(number: int, total_bits: int, chunk_size: int) -> np.ndarray:
    """Convert an integer to M-bit chunks.

    Args:
        number: The input integer
        total_bits: Total number of bits in the integer (N)
        chunk_size: Size of each chunk in bits (M)

    Returns:
        Array of integers, each representing an M-bit chunk

    Raises:
        ValueError: If total_bits is not a multiple of chunk_size
    """
    if total_bits % chunk_size != 0:
        raise ValueError("Total bits must be an exact multiple of the chunk size.")

    # Format the number into a zero-padded binary string of N bits
    binary_string = format(number, f"0{total_bits}b")

    # Split the binary string into chunks of M bits
    chunks = []
    for i in range(0, total_bits, chunk_size):
        chunk_str = binary_string[i : i + chunk_size]
        chunks.append(int(chunk_str, 2))

    return np.array(chunks, dtype=int)


class ModemTx:
    """TX modem for modulation and signal processing.

    This class handles:
    - Symbol modulation (M-QAM)
    - Upsampling
    - Pulse shaping
    - Preamble generation
    - Sync codeword generation
    """

    def __init__(self, config: PhyConfig) -> None:
        """Initialize TX modem.

        Args:
            config: Physical layer configuration
        """
        self.config = config
        self.qam = modem.Qam(config.modulation_order)
        self.sps = config.samples_per_symbol

        # Initialize RRC filter
        rrc = fir_filter.RootRaisedCosine(
            config.rrc_rolloff, config.rrc_span, config.samples_per_symbol
        )
        self.filter_coeff = np.array(rrc.get_coefficients())

        logger.info(
            f"TX Modem initialized - {config.modulation_order}-QAM, "
            f"SPS={config.samples_per_symbol}, RRC β={config.rrc_rolloff}"
        )

    def modulate_payload(self, payload: np.ndarray) -> np.ndarray:
        """Modulate payload symbols to complex constellation points.

        Args:
            payload: Array of integer symbols (0 to M-1)

        Returns:
            Array of complex modulated symbols
        """
        modulated = np.zeros(len(payload), dtype=complex)
        for idx, val in enumerate(payload):
            modulated[idx] = self.qam.modulate(int(val))
        return modulated

    def upsample(self, data: np.ndarray) -> np.ndarray:
        """Upsample data by inserting zeros.

        Args:
            data: Input data

        Returns:
            Upsampled data with zeros inserted
        """
        upsampled = np.zeros(len(data) * self.sps, dtype=data.dtype)
        upsampled[:: self.sps] = data
        return upsampled

    def pulse_shape(self, data: np.ndarray) -> np.ndarray:
        """Apply RRC pulse shaping filter.

        Args:
            data: Upsampled data

        Returns:
            Pulse-shaped data
        """
        return np.convolve(data, self.filter_coeff, mode="same")

    def get_pll_preamble(self) -> np.ndarray:
        """Generate QPSK preamble for PLL synchronization.

        Returns:
            QPSK modulated preamble symbols
        """
        preamble_length = self.config.pll_preamble_length
        preamble = np.array(
            [1.0 + 1.0j, -1.0 + 1.0j, -1.0 - 1.0j, 1.0 - 1.0j] * (preamble_length // 4)
        )
        return preamble

    def get_nasa_codeword(self) -> np.ndarray:
        """Generate NASA sync codeword with good autocorrelation.

        Returns:
            Modulated NASA codeword symbols
        """
        code_length = self.config.nasa_codeword_bits
        if code_length not in NASA_CODEWORDS:
            raise ValueError(
                f"NASA codeword length {code_length} not supported. "
                f"Must be one of {list(NASA_CODEWORDS.keys())}"
            )

        codeword = NASA_CODEWORDS[code_length]
        bits_per_symbol = int(np.log2(self.config.modulation_order))
        code_symbols = int_to_m_bit_chunks(codeword, code_length, bits_per_symbol)

        # Modulate the codeword
        modulated_code = np.zeros(len(code_symbols), dtype=complex)
        for idx, val in enumerate(code_symbols):
            modulated_code[idx] = self.qam.modulate(int(val))

        return modulated_code

    def build_frame(self, payload: np.ndarray) -> np.ndarray:
        """Build a complete TX frame with codeword, preamble, and payload.

        Args:
            payload: Integer symbols to transmit (0 to M-1)

        Returns:
            Complete frame ready for transmission (pulse-shaped, upsampled)
        """
        # Get sync codeword and preamble
        codeword = self.get_nasa_codeword()
        preamble = self.get_pll_preamble()

        # Modulate payload
        modulated_payload = self.modulate_payload(payload)

        # Concatenate: codeword + preamble + payload
        frame_symbols = np.concatenate((codeword, preamble, modulated_payload))

        # Upsample
        upsampled = self.upsample(frame_symbols)

        # Pulse shape
        pulse_shaped = self.pulse_shape(upsampled)

        # Scale to ADC range
        pulse_shaped *= 2**14

        return pulse_shaped
