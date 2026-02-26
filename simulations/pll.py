"""Simulation of PLL in action"""

from dataclasses import dataclass

import matplotlib.pyplot as plt
import numpy as np
from qpsk_modulation import QPSK, QPSK_demod


@dataclass
class state:
    theta = 0  # Phase estimate
    integrator = 0  # integrator state


@dataclass
class parameters:
    num_symbols = 2000
    loop_bandwidth = 300_000  # Needs to be larger than 120 kHz
    rf_frequency = 2_400_000_000
    sampling_rate = 50_000_000
    oversampling_factor = 8
    symbol_rate = sampling_rate / oversampling_factor
    frequency_offset = -500
    k_p = 0.0222
    k_i = 2.4e-4


def open_loop(z: np.ndarray, k_p: float, k_i: float, D: int = 0):
    return z ** (-D) * (k_p * z + (k_i - k_p)) / (z - 1) ** 2


def closed_loop(z: np.ndarray, k_p: float, k_i: float):
    g = open_loop(z, k_p, k_i)
    return g / (1 + g)


if __name__ == "__main__":
    omega = np.logspace(-5, np.log10(np.pi), 1000)
    z = np.exp(1j * omega)

    closed_loop_filter = closed_loop(z, parameters.k_p, parameters.k_i)
    loop_filter_db = 20 * np.log10(np.abs(closed_loop_filter))

    fig, ax = plt.subplots(1, 1)
    ax.semilogx(omega, loop_filter_db)
    ax.set_title("Loop filter amplitude response")
    ax.grid()

    # Generate data to transmit
    data = np.array([0, 1, 3, 2] * (parameters.num_symbols // 4))
    data_symbols = QPSK(data)

    # Add white noise error
    noise = (
        (np.random.randn(len(data_symbols)) + 1j * np.random.randn(len(data_symbols)))
        / np.sqrt(2)
        * np.sqrt(0.02)
    )
    # data_symbols += noise

    # Add phase error
    n = np.arange(len(data_symbols))
    data_symbols *= np.exp(
        1j * 2 * np.pi * parameters.frequency_offset / parameters.symbol_rate * n
    )

    e = np.zeros(len(data_symbols))
    theta = np.zeros(len(data_symbols))
    phase_locked_data = np.zeros(len(data_symbols), dtype=complex)
    for i, x in enumerate(data_symbols):
        x *= np.exp(-1j * state.theta)
        phase_locked_data[i] = x

        closest_symbol = QPSK_demod(x)

        e[i] = np.angle(x * np.conj(closest_symbol))

        state.integrator = state.integrator + parameters.k_i * e[i]
        state.theta += state.integrator + parameters.k_p * e[i]
        theta[i] = state.theta

    # Plot generated symbols as received on the Rx side
    fig, ax = plt.subplots(1, 1, tight_layout=True)
    ax.plot(e, label="error")
    ax2 = ax.twinx()
    ax2.plot(theta, label="theta", color="C1")
    ax.set_ylabel("Error (rad)")
    ax2.set_ylabel("Theta (rad)")

    ax.legend()
    ax2.legend()
    ax.grid()

    # Plot generated symbols as received on the Rx side
    fig, ax = plt.subplots(1, 1, tight_layout=True)
    ax.set_box_aspect(1)
    ax.scatter(data_symbols.real, data_symbols.imag, alpha=0.2)
    ax.scatter(
        phase_locked_data.real, phase_locked_data.imag, alpha=n / len(data_symbols)
    )
    ax.grid()

    plt.show()
