import modem
import numpy as np

NASA_CODEWORDS: dict[int, int] = {
    32: 0x89445BC1,
    36: 0xC6859AE80,
    64: 0xEC10845E8B3CB0AC,
}


class ModemTx:
    def __init__(self, qam: modem.Qam, sps: int) -> None:
        self.qam = qam
        self.sps = sps
        self.filter_coeff = None

    def modulate_payload(self, payload: np.ndarray):
        """Modulate payload"""

        _modulated = np.zeros_like(payload, dtype=complex)
        for idx, val in enumerate(payload):
            _modulated[idx] = self.qam.modulate(val)
        return _modulated

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

    def add_codeword(self, data: np.ndarray, code_length: int = 32) -> bytes:
        """Prefix data with a codeword with nice autocorrelation features"""

        codeword = NASA_CODEWORDS[code_length]
        return np.concatenate((codeword, data))
