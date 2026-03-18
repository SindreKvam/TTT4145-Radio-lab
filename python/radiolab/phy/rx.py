import numpy as np
from fir_filter import RootRaisedCosine
from scipy import signal


class ModemRx:
    def __init__(self, rrc_filter: RootRaisedCosine):
        self.rrc_coeff = rrc_filter.get_coefficients()
        self.filter_state = signal.lfiltic(self.rrc_coeff, 1, 0)

    def matched_filtering(self, samples: np.ndarray):
        """Perform matched filtering of data"""

        _matched_filtered_data, self.filter_state = signal.lfilter(
            self.rrc_coeff, 1, samples, zi=self.filter_state
        )
        return _matched_filtered_data

    def detect_codeword(
        self, samples: np.ndarray, code: np.ndarray, threshold: float = None
    ):
        """Find the largest peak in the data based on correlation"""

        _correlation = np.correlate(samples / np.max(samples), code, mode="same")
        _correlation = np.pow(np.abs(_correlation), 2)
        if threshold is None:
            return np.argmax(_correlation)

        return signal.find_peaks(_correlation, height=threshold)

    def recover_timing(self, samples: np.ndarray):
        raise NotImplementedError

    def phase_locked_loop(self, sampled: np.ndarray):
        raise NotImplementedError
