import numpy as np
from modem import Qam
from pll import Pll
from scipy import signal


class ModemRx:
    def __init__(self, qam: Qam, sps: int, filter_coeff: np.ndarray):
        self.qam = qam
        self.sps = sps
        self.filter_coeff = filter_coeff
        self.filter_state = signal.lfiltic(self.filter_coeff, 1, 0)
        self.last_coarse_cfo_omega = 0.0
        self.k_p = 0.0222
        self.k_i = 0.00024
        self.qam_lut = np.asarray(self.qam.get_lookup_table(), dtype=np.complex64)
        self.pll = Pll(self.k_p, self.k_i)

    def matched_filtering(self, samples: np.ndarray):
        """Perform matched filtering of data"""

        _matched_filtered_data, self.filter_state = signal.lfilter(
            self.filter_coeff, 1, samples, zi=self.filter_state
        )
        return _matched_filtered_data

    def _correlate_with_codeword(
        self, samples: np.ndarray, code: np.ndarray
    ) -> np.ndarray:
        """Correlate with codeword"""

        _correlation = np.correlate(samples / np.max(samples), code, mode="same")
        _correlation = np.pow(np.abs(_correlation), 2)
        return _correlation

    def detect_codeword(
        self, samples: np.ndarray, code: np.ndarray, threshold: float = None
    ):
        """Find the largest peak in the data based on correlation"""

        _correlation = self._correlate_with_codeword(samples, code)

        if threshold is None:
            return np.argmax(_correlation)

        return signal.find_peaks(_correlation, height=threshold)[0]

    def remove_codeword(self, samples: np.ndarray, peak_index: int, code_length: int):
        return samples[peak_index + code_length // 2 :]

    def coarse_frequency_offset(self, samples: np.ndarray):
        raise NotImplementedError

    def recover_timing(self, samples: np.ndarray):
        offset = np.argmax(np.abs(samples[: self.sps]))
        return samples[offset :: self.sps]

    def automatic_gain_control(self, samples: np.ndarray):
        """"""
        raise NotImplementedError

    def phase_locked_loop(self, samples: np.ndarray, pll_preamble: np.ndarray = None):
        """"""
        phase_locked_data = self.pll.phase_locked_loop_array(
            samples, self.qam_lut, pll_preamble
        )
        return np.asarray(phase_locked_data, dtype=samples.dtype)
