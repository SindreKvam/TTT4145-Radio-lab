import logging
from pathlib import Path

import fir_filter
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


@pytest.mark.parametrize("beta", [0.2, 0.707])
@pytest.mark.parametrize("span", [4, 8, 10])
@pytest.mark.parametrize("sps", [4, 8, 16])
def test_matched_filter(beta, span, sps):
    rrc = fir_filter.RootRaisedCosine(beta, span, sps)
    rrc_coeff = np.array(rrc.get_coefficients())

    pytest.approx(1, np.sum(rrc_coeff))

    plt.figure()
    plt.stem(rrc_coeff)
    plt.title(f"$\\beta = {beta}$, span = {span}, sps = {sps}")
    plt.grid()
    plt.savefig(output_folder / f"rrc_{beta}_{span}_{sps}.png")
    plt.close("all")


@pytest.mark.parametrize("span", [2, 10])
@pytest.mark.parametrize("sps", [4, 8, 16])
@pytest.mark.parametrize("mode", ["full", "same"])
def test_matched_filter_filtering(span, sps, mode, beta: float = 0.2, mqam: int = 4):
    qam = modem.Qam(mqam)

    # Create data
    data = np.random.randint(mqam, size=50)

    modulated_data = np.zeros_like(data, dtype=complex)
    for idx, value in enumerate(data):
        modulated_data[idx] = qam.modulate(value)

    oversampled_data = np.zeros((len(data) * sps,), dtype=complex)
    oversampled_data[::sps] = modulated_data

    rrc = fir_filter.RootRaisedCosine(beta, span, sps)
    rrc_coeff = np.array(rrc.get_coefficients())

    pulse_shaped = np.convolve(oversampled_data, rrc_coeff, mode=mode)
    matched_filter = np.convolve(pulse_shaped, rrc_coeff, mode=mode)

    plt.figure()
    plt.scatter(oversampled_data.real, oversampled_data.imag, label="Oversampled data")
    plt.scatter(pulse_shaped.real, pulse_shaped.imag, label="Pulse shaped data")
    plt.scatter(
        matched_filter.real,
        matched_filter.imag,
        label="Matched filtered data",
    )
    plt.legend()
    plt.savefig(
        output_folder / f"scatter_matched_filter_span={span}_sps={sps}_mode={mode}.png",
        dpi=300,
    )

    fig, (real_ax, imag_ax) = plt.subplots(2, 1, tight_layout=True)

    real_ax.plot(oversampled_data.real, label="Oversampled data")
    imag_ax.plot(oversampled_data.imag, label="Oversampled data")
    real_ax.plot(pulse_shaped.real, label="Pulse shaped data")
    imag_ax.plot(pulse_shaped.imag, label="Pulse shaped data")
    real_ax.plot(matched_filter.real, label="Match filtered data")
    imag_ax.plot(matched_filter.imag, label="Match filtered data")

    fig.suptitle(
        "Transmitted data before and after pulse shaping filter\n"
        + "$\\beta = {beta}$, span = {span}, sps = {sps}"
    )

    real_ax.legend()
    imag_ax.legend()

    plt.savefig(
        output_folder / f"matched_filter_span={span}_sps={sps}_mode={mode}.png", dpi=300
    )
    plt.close("all")
