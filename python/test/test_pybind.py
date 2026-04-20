import logging
from pathlib import Path

import matplotlib.pyplot as plt
import modem
import numpy as np
import pytest
from pll import Pll

logger = logging.getLogger(__name__)


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
    plt.suptitle(title)
    plt.axis("equal")
    plt.ylabel("Quadrature (Q)")
    plt.xlabel("In-phase (I)")
    plt.ylim([-1.4, 1.4])
    plt.grid(alpha=0.3)
    plt.savefig(output_folder / title)
    plt.close("all")


@pytest.mark.parametrize("num_symbols", [4, 16, 64, 256])
def test_modem_array_roundtrip(num_symbols):
    qam = modem.Qam(num_symbols)
    data = np.random.randint(0, num_symbols, size=(512,), dtype=np.uint16)

    modulated = np.asarray(qam.modulate_array(data))
    demodulated = np.asarray(qam.demodulate_array(modulated))

    assert modulated.shape == data.shape
    assert demodulated.shape == data.shape
    assert np.array_equal(demodulated, data)


@pytest.mark.parametrize("k_p,k_i", [[0.0222, 0.00024]])
@pytest.mark.parametrize("pll_preamble_length", [300, 600, 1200])
@pytest.mark.parametrize("phase_offset", [30, 45])
@pytest.mark.parametrize("frequency_offset", [0.1, 1, 10])
def test_phase_locked_loop(
    k_p: float,
    k_i: float,
    pll_preamble_length: int,
    phase_offset: int,
    frequency_offset: int,
):
    pll = Pll(k_p, k_i)
    qam_16 = modem.Qam(16)

    data_length = int(pll_preamble_length * 1.5)
    data = np.random.randint(0, 16, size=(data_length,), dtype=np.uint16)
    modulated_data = np.asarray(qam_16.modulate_array(data))

    _preamble = np.array(
        [1.0 + 1.0j, -1.0 + 1.0j, -1.0 - 1.0j, 1.0 - 1.0j] * (pll_preamble_length // 4)
    )

    data = np.concatenate((_preamble, modulated_data))

    t = np.arange(len(data))
    data *= np.exp(
        -1j * frequency_offset * np.pi / 180 * t
    )  # 0.1 degree phase shift per sample
    data *= np.exp(-1j * phase_offset * np.pi / 180)  # 45 degree phase shift

    phase_locked_data, phase_error, theta_history = (
        pll.phase_locked_loop_with_stats_array(
            data,
            np.array(qam_16.get_lookup_table()),
            _preamble,
        )
    )

    # phase_error *= 180 / np.pi
    # theta_history *= 180 / np.pi

    fig, ax = plt.subplots(2, 1, constrained_layout=True)
    # ax[0].scatter(
    #     data.real[:pll_preamble_length],
    #     data.imag[:pll_preamble_length],
    #     label="PLL preamble",
    #     alpha=np.linspace(0, 0.3, pll_preamble_length),
    # )
    ax[0].scatter(
        data.real[pll_preamble_length:],
        data.imag[pll_preamble_length:],
        label="Received data",
        alpha=np.linspace(0.3, 0.6, data_length),
    )
    # ax[0].scatter(
    #     phase_locked_data.real[:pll_preamble_length],
    #     phase_locked_data.imag[:pll_preamble_length],
    #     label="Locked preamble",
    # )
    ax[0].scatter(
        phase_locked_data.real[pll_preamble_length:],
        phase_locked_data.imag[pll_preamble_length:],
        label="Locked data",
        alpha=np.linspace(0.4, 0.7, data_length),
    )

    pll_x = np.arange(0, len(phase_error[:pll_preamble_length]))
    payload_x = np.arange(
        pll_preamble_length,
        pll_preamble_length + len(phase_error[pll_preamble_length:]),
    )

    ax[1].plot(pll_x, phase_error[:pll_preamble_length], label="")
    ax[1].plot(0, phase_error[0], color="red", marker="o")
    # tw_ax = ax[2].twinx()
    # tw_ax.plot(theta_history[:pll_preamble_length] * 180 / np.pi, color="C1")

    ax[1].plot(payload_x, phase_error[pll_preamble_length:])
    ax[1].plot(
        pll_preamble_length, phase_error[pll_preamble_length], color="red", marker="o"
    )
    # tw_ax.plot(theta_history[pll_preamble_length:] * 180 / np.pi, color="C1")

    title = (
        f"pll_Kp={k_p}_Ki={k_i}_len={pll_preamble_length}_F_off={frequency_offset}deg"
    )

    for a in ax.flatten():
        a.legend()

    plt.savefig(output_folder / (title + ".svg"))
    plt.close("all")
