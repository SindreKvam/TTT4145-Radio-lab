import logging

import numpy as np
import pytest
from modem import Qam

logger = logging.getLogger(__name__)


@pytest.fixture
def preamble(preamble_length: int):
    """Generate a preamble"""

    return np.array(
        [1.0 + 1.0j, -1.0 + 1.0j, -1.0 - 1.0j, 1.0 - 1.0j] * (preamble_length // 4)
    )


@pytest.fixture
def modulated_data_with_preamble(
    preamble,
    data_length: float,
    modulation: int,
):
    """Generate random data"""

    logger.info(f"Generating {modulation}-QAM data")

    qam = Qam(modulation)

    _data = np.random.randint(0, modulation, size=(data_length,))
    modulated_data = np.asarray(qam.modulate_array(_data))

    data = np.concatenate((preamble, modulated_data))

    return data


@pytest.fixture
def modulated_noisy_data_with_preamble(modulated_data_with_preamble, snr_db: float):
    """Generate and return noisy data of a given length"""

    logger.info(f"Generating noise with SNR={snr_db}")

    # Add noise based on SNR
    _data_power = np.mean(np.abs(modulated_data_with_preamble) ** 2)
    _snr_linear = 10 ** (snr_db / 10)
    _noise_power = _data_power / _snr_linear
    _noise_std = np.sqrt(_noise_power / 2)  # Spread accross real and imag
    noise = _noise_std * (
        np.random.standard_normal(modulated_data_with_preamble.shape)
        + 1j * np.random.standard_normal(modulated_data_with_preamble.shape)
    )

    return modulated_data_with_preamble + noise
