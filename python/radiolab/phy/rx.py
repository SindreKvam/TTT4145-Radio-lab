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

    def correlate_with_codeword(
        self, samples: np.ndarray, code: np.ndarray
    ) -> np.ndarray:
        """Return squared-magnitude correlation for synchronization."""

        if len(samples) == 0:
            return np.array([], dtype=float)

        peak = np.max(np.abs(samples))
        if (not np.isfinite(peak)) or peak <= 0:
            return np.zeros(len(samples), dtype=float)

        _correlation = np.correlate(samples / peak, code, mode="same")
        _correlation = np.pow(np.abs(_correlation), 2)
        return _correlation

    def detect_peak(
        self, correlation: np.ndarray, threshold: float = None
    ) -> tuple[int | None, float]:
        """Detect strongest correlation peak and return index and value."""

        if len(correlation) == 0:
            return None, 0.0

        if threshold is None:
            peak_index = int(np.argmax(correlation))
            return peak_index, float(correlation[peak_index])

        peaks, properties = signal.find_peaks(correlation, height=threshold)
        if len(peaks) == 0:
            return None, 0.0

        best_idx = int(np.argmax(properties["peak_heights"]))
        peak_index = int(peaks[best_idx])
        return peak_index, float(properties["peak_heights"][best_idx])

    def peak_to_start(
        self, peak_index: int, code_length: int, signal_length: int | None = None
    ) -> int:
        """Map correlation peak index to estimated codeword start index."""

        start_index = int(peak_index - code_length // 2)
        if signal_length is None:
            return max(0, start_index)

        if signal_length <= 0:
            return 0
        return int(np.clip(start_index, 0, signal_length - 1))

    def remove_codeword_from_start(
        self, samples: np.ndarray, start_index: int, code_length: int
    ) -> np.ndarray:
        """Remove codeword when start index is known."""

        end_index = int(start_index + code_length)
        if end_index <= 0:
            return samples
        if end_index >= len(samples):
            return np.array([], dtype=samples.dtype)
        return samples[end_index:]

    def detect_codeword(
        self, samples: np.ndarray, code: np.ndarray, threshold: float = None
    ):
        """Find the largest peak in the data based on correlation"""

        _correlation = self.correlate_with_codeword(samples, code)

        if threshold is None:
            return np.argmax(_correlation)

        return signal.find_peaks(_correlation, height=threshold)[0]

    def remove_codeword(self, samples: np.ndarray, peak_index: int, code_length: int):
        start_index = self.peak_to_start(peak_index, code_length, len(samples))
        return self.remove_codeword_from_start(samples, start_index, code_length)

    def coarse_frequency_offset(self, samples: np.ndarray):
        raise NotImplementedError

    def recover_timing(self, samples: np.ndarray):
        offset = 0
        highest_val = 0
        for _offset in range(self.sps):
            val = np.sum(np.abs(samples[_offset :: self.sps]))
            if val > highest_val:
                highest_val = val
                offset = _offset

        return samples[offset :: self.sps]

    def automatic_gain_control(
        self,
        samples: np.ndarray,
        preamble_length: int,
        target_magnitude: float = np.sqrt(2.0),
    ) -> tuple[np.ndarray, float] | tuple[None, None]:
        """Normalize signal gain using only the known preamble segment.

        Returns a tuple of (scaled_samples, gain). If gain estimation fails,
        returns (None, None).
        """

        if len(samples) == 0:
            return None, None

        preamble_len = int(min(max(preamble_length, 1), len(samples)))
        preamble = samples[:preamble_len]

        # Phase-invariant gain estimate from preamble RMS.
        preamble_rms = np.sqrt(np.mean(np.abs(preamble) ** 2))
        if (not np.isfinite(preamble_rms)) or preamble_rms <= 0:
            return None, None

        gain = float(target_magnitude / preamble_rms)
        if (not np.isfinite(gain)) or gain <= 0:
            return None, None

        return samples * gain, gain

    def phase_locked_loop(self, samples: np.ndarray, pll_preamble: np.ndarray = None):
        """"""
        phase_locked_data = self.pll.phase_locked_loop_array(
            samples, self.qam_lut, pll_preamble
        )
        return np.asarray(phase_locked_data, dtype=samples.dtype)

    def phase_locked_loop_with_stats(
        self, samples: np.ndarray, pll_preamble: np.ndarray = None
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Run PLL and return (derotated, phase_error, theta_history)."""

        phase_locked_data, phase_error, theta_history = (
            self.pll.phase_locked_loop_with_stats_array(
                samples,
                self.qam_lut,
                pll_preamble,
            )
        )
        return (
            np.asarray(phase_locked_data, dtype=samples.dtype),
            np.asarray(phase_error, dtype=float),
            np.asarray(theta_history, dtype=float),
        )
