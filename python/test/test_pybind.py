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


@pytest.mark.slow
@pytest.mark.parametrize("k_p,k_i", [[0.0222, 0.00024]])
@pytest.mark.parametrize(
    "preamble_length,data_length", [[300, 450], [600, 900], [1200, 1800]]
)
@pytest.mark.parametrize("phase_offset", [30, 45])
@pytest.mark.parametrize("frequency_offset", [0.1, 1, 10])
@pytest.mark.parametrize("snr_db", [30, 20, 10])
@pytest.mark.parametrize("modulation", [4, 16, 64])
def test_phase_locked_loop(
    preamble,
    modulated_noisy_data_with_preamble,
    k_p: float,
    k_i: float,
    modulation: int,
    snr_db: float,
    preamble_length: int,
    data_length: int,
    phase_offset: int,
    frequency_offset: int,
):

    data = modulated_noisy_data_with_preamble

    # Add frequency and phase shift
    t = np.arange(len(data))
    data *= np.exp(-1j * frequency_offset * np.pi / 180 * t)
    data *= np.exp(-1j * phase_offset * np.pi / 180)

    # Perform phase locked loop
    pll = Pll(k_p, k_i)
    qam = modem.Qam(modulation)

    phase_locked_data, phase_error, theta_history = (
        pll.phase_locked_loop_with_stats_array(
            data,
            np.array(qam.get_lookup_table()),
            preamble,
        )
    )

    # Generate plots
    fig, ax = plt.subplots(2, 1, constrained_layout=True, figsize=(3.5, 5))
    fig.suptitle("Phase locked loop")
    ax[0].set_title(
        f"$p_e={phase_offset:.2f}$, $f_e={frequency_offset:.2f}$"
        + f", SNR={snr_db} dB, K_p={k_p}, K_i={k_i}",
    )

    # Plot constellation diagram of received vs phase locked data
    ax[0].set_ylabel("Quadrature (Q)")
    ax[0].set_xlabel("In-phase (I)")
    ax[0].scatter(
        data.real[preamble_length:],
        data.imag[preamble_length:],
        label="Received data",
        alpha=np.linspace(0.3, 0.6, data_length),
    )
    ax[0].scatter(
        phase_locked_data.real[preamble_length:],
        phase_locked_data.imag[preamble_length:],
        label="Locked data",
        alpha=np.linspace(0.4, 0.7, data_length),
    )

    # Plot the phase error from the PLL
    pll_x = np.arange(0, len(phase_error[:preamble_length]))
    payload_x = np.arange(
        preamble_length,
        preamble_length + len(phase_error[preamble_length:]),
    )

    ax[1].plot(
        pll_x,
        phase_error[:preamble_length],
        label="Phase error preamble",
    )
    ax[1].scatter(
        0,
        phase_error[0],
        color="C0",
        marker="d",
        label="$p_{e0}=" + f"{phase_error[0]:.2f}$",
    )
    tw_ax = ax[1].twinx()
    tw_ax.plot(
        pll_x,
        theta_history[:preamble_length] % (2 * np.pi) - np.pi,
        "--",
        color="C0",
        alpha=0.5,
    )

    ax[1].plot(
        payload_x,
        phase_error[preamble_length:],
        label="Phase error data",
    )
    ax[1].scatter(
        preamble_length,
        phase_error[preamble_length],
        color="C1",
        marker="d",
        label="$p_{es}=" + f"{phase_error[preamble_length]:.2f}$",
    )
    tw_ax.plot(
        payload_x,
        theta_history[preamble_length:] % (2 * np.pi) - np.pi,
        "--",
        color="C1",
        alpha=0.5,
    )
    tw_ax.set_ylim([-2 * np.pi, 2 * np.pi])

    ax[1].set_ylabel("Phase error (rad)")
    ax[1].set_xlabel("Sample (n)")
    tw_ax.set_ylabel("Phase adjustment (rad)")
    tw_ax.grid()

    title = (
        f"pll_M={modulation}_Kp={k_p}_Ki={k_i}_len={preamble_length}"
        + f"_F_off={frequency_offset}deg"
        + f"_P_off={phase_offset}deg"
        + f"_SNR={snr_db}dB"
    )

    for a in ax.flatten():
        a.legend()

    plt.savefig(output_folder / (title + ".svg"))
    plt.savefig(output_folder / (title + ".png"), dpi=300)
    plt.close("all")
