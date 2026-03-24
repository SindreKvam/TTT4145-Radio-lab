import numpy as np
from modem import Qam
from scipy import signal


class ModemRx:
    def __init__(self, qam: Qam, sps: int, filter_coeff: np.ndarray):
        self.qam = qam
        self.sps = sps
        self.filter_coeff = filter_coeff
        self.filter_state = signal.lfiltic(self.filter_coeff, 1, 0)

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
        k_p = 0.0222
        k_i = 0.00024

        e = np.zeros(len(samples))
        theta = np.zeros(len(samples))
        phase_locked_data = np.zeros_like(samples)

        if pll_preamble is not None:
            pll_preamble_length = len(pll_preamble)
        else:
            pll_preamble_length = 0

        self.theta = self.integrator = 0

        # Phase locked loop
        # TODO: implement this in Cpp instead
        for i, x in enumerate(samples):
            x *= np.exp(-1j * self.theta)
            phase_locked_data[i] = x

            # Phase detector
            if i < pll_preamble_length:
                closest_symbol = pll_preamble[i]
            else:
                closest_symbol = self.qam.modulate(self.qam.demodulate(x))

            e[i] = np.imag(x * np.conj(closest_symbol))
            # e[i] = np.angle(x * np.conj(closest_symbol))

            # Loop filter
            self.integrator = self.integrator + k_i * e[i]
            self.theta += self.integrator + k_p * e[i]
            theta[i] = self.theta

        return phase_locked_data
