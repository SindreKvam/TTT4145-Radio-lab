import modem
import numpy as np

from radiolab.tx import int_to_m_bit_chunks

NASA_CODEWORDS: dict[int, int] = {
    32: 0x89445BC1,
    36: 0xC6859AE80,
    64: 0xEC10845E8B3CB0AC,
}


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
