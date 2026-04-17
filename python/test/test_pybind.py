import logging
from pathlib import Path

import matplotlib.pyplot as plt
import modem
import numpy as np
import pytest

logger = logging.getLogger(__name__)

output_folder = Path(__file__).parent / "pytest-output/"
output_folder.mkdir(parents=True, exist_ok=True)


@pytest.mark.parametrize("num_symbols", [4, 16, 64, 256, 1024])
def test_modem(num_symbols):
    qam = modem.Qam(num_symbols)
    qam_lookup_table = np.array(qam.get_lookup_table(), dtype=complex)

    plt.figure()
    plt.scatter(qam_lookup_table.real, qam_lookup_table.imag)

    plt.title(f"{num_symbols}-QAM")
    plt.axis("equal")
    plt.ylabel("Quadrature")
    plt.xlabel("In-phase")
    plt.grid()
    plt.show()


@pytest.mark.parametrize("num_symbols", [4, 16, 64, 256])
def test_modem_array_roundtrip(num_symbols):
    qam = modem.Qam(num_symbols)
    data = np.random.randint(0, num_symbols, size=(512,), dtype=np.uint16)

    modulated = np.asarray(qam.modulate_array(data))
    demodulated = np.asarray(qam.demodulate_array(modulated))

    assert modulated.shape == data.shape
    assert demodulated.shape == data.shape
    assert np.array_equal(demodulated, data)
