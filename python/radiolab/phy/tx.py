import modem
import numpy as np

NASA_CODEWORDS: dict[int, int] = {
    32: 0x89445BC1,
    36: 0xC6859AE80,
    64: 0xEC10845E8B3CB0AC,
}


def int_to_m_bit_chunks(number, total_bits, chunk_size) -> np.ndarray:
    """
    Converts an integer to a list of m-bit integer chunks.

    Args:
        number (int): The input integer.
        total_bits (int): The total number of bits for the integer (N).
        chunk_size (int): The size of each chunk in bits (M).

    Returns:
        list: A list of integers, each representing an m-bit chunk.
    """
    if total_bits % chunk_size != 0:
        raise ValueError("Total bits must be an exact multiple of the chunk size.")

    # Format the number into a zero-padded binary string of N bits
    binary_string = format(number, f"0{total_bits}b")

    # Split the binary string into chunks of M bits
    chunks = []
    for i in range(0, total_bits, chunk_size):
        chunk_str = binary_string[i : i + chunk_size]
        # Convert each binary chunk string back to an integer
        chunks.append(int(chunk_str, 2))

    return np.array(chunks, dtype=int)


class ModemTx:
    def __init__(self, qam: modem.Qam, sps: int, filter_coeff: np.ndarray) -> None:
        self.qam = qam
        self.sps = sps
        self.filter_coeff = filter_coeff

        self.M = len(self.qam.get_lookup_table())

    def modulate_payload(self, payload: np.ndarray):
        """Modulate payload"""
        return np.asarray(self.qam.modulate_array(payload), dtype=complex)

    def upsample(self, data: np.ndarray):
        """Upsample data by "sps" times."""

        _upsampled = np.zeros_like(data, shape=(len(data) * self.sps,))
        _upsampled[:: self.sps] = data
        return _upsampled

    def add_pll_preamble(
        self, data: np.ndarray, preamble_length: int = 600
    ) -> np.ndarray:
        """Prefix QPSK modulated preamble to the data"""

        _preamble = np.array(
            [1.0 + 1.0j, -1.0 + 1.0j, -1.0 - 1.0j, 1.0 - 1.0j] * (preamble_length // 4)
        )
        return np.concatenate((_preamble, data))

    def pulse_shape(self, data: np.ndarray) -> np.ndarray:
        """Pulse shape data by convolving with filter coefficients"""

        return np.convolve(data, self.filter_coeff, mode="same")

    def _get_codeword(self, code_length):
        return np.array(
            int_to_m_bit_chunks(
                NASA_CODEWORDS[code_length], code_length, int(np.log2(self.M))
            ),
            dtype=int,
        )

    def add_codeword(self, data: np.ndarray, code_length: int = 32) -> bytes:
        """Prefix data with a codeword with nice autocorrelation features"""

        codeword = self._get_codeword(code_length)
        return np.concatenate((codeword, data))

    def add_modulated_codeword(self, data: np.ndarray, code_length: int = 32):
        """Prefix data with a modulated codeword with nice autocorrelation features"""

        codeword = self._get_codeword(code_length)
        codeword = self.modulate_payload(codeword)
        return np.concatenate((codeword, data))
