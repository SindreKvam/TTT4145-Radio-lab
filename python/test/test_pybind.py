import logging
from pathlib import Path

import matplotlib.pyplot as plt
import modem
import numpy as np
import pytest

logger = logging.getLogger(__name__)


parent_folder = Path(__file__).parent

plt.style.use(str(parent_folder.parent / "style.mplstyle"))

output_folder = Path(__file__).parent / "pytest-output/"
output_folder.mkdir(parents=True, exist_ok=True)


@pytest.mark.parametrize("num_symbols", [4, 16, 64, 256, 1024])
def test_modem(num_symbols):
    qam = modem.Qam(num_symbols)
    qam_lookup_table = np.array(qam.get_lookup_table(), dtype=complex)

    plt.figure()
    plt.scatter(qam_lookup_table.real, qam_lookup_table.imag, marker="o")

    for idx, const in enumerate(qam_lookup_table):
        plt.text(
            const.real + 0.04,
            const.imag + 0.04,
            bin(idx)[2:].zfill(int(np.log2(num_symbols))),
            color="blue",
        )

    title = f"{num_symbols}-QAM Constellation"
    plt.title(title)
    plt.axis("equal")
    plt.ylabel("Quadrature (Q)")
    plt.xlabel("In-phase (I)")
    plt.ylim([-1.2, 1.2])
    plt.grid(alpha=0.3)
    plt.savefig(output_folder / (title + ".svg"), dpi=300)


@pytest.mark.parametrize("num_symbols", [4, 16, 64, 256])
def test_modem_array_roundtrip(num_symbols):
    qam = modem.Qam(num_symbols)
    data = np.random.randint(0, num_symbols, size=(512,), dtype=np.uint16)

    modulated = np.asarray(qam.modulate_array(data))
    demodulated = np.asarray(qam.demodulate_array(modulated))

    assert modulated.shape == data.shape
    assert demodulated.shape == data.shape
    assert np.array_equal(demodulated, data)
