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
    num_symbols = 1200
    oversampling_factor = 8
    loop_bandwidth = 300_000  # Needs to be larger than 120 kHz
    sampling_rate = 50_000_000
    frequency_offset = 50_000
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
    ax.grid()

    # Generate data to transmit
    data = np.array([0, 1, 2, 3] * (parameters.num_symbols // 4))
    data_symbols = QPSK(data)

    # noise = (
    #     (np.random.randn(len(data_symbols)) + 1j * np.random.randn(len(data_symbols)))
    #     / np.sqrt(2)
    #     * np.sqrt(0.10)
    # )

    # data_symbols += noise
    n = np.arange(len(data_symbols))
    data_symbols *= np.exp(
        1j * 2 * np.pi * parameters.frequency_offset / parameters.sampling_rate * n
    )

    # Plot generated symbols as received on the Rx side
    fig, ax = plt.subplots(1, 1, tight_layout=True)
    ax.set_box_aspect(1)
    ax.scatter(data_symbols.real, data_symbols.imag)
    ax.grid()

    e = np.zeros(len(data_symbols))
    for i, x in enumerate(data_symbols):
        x *= np.exp(-1j * state.theta)

        closest_symbol = QPSK_demod(x)

        e[i] = np.angle(x * np.conj(closest_symbol))

        state.integrator = state.integrator + parameters.k_i * e[i]
        state.theta += state.integrator + parameters.k_p * e[i]

    # Plot generated symbols as received on the Rx side
    fig, ax = plt.subplots(1, 1, tight_layout=True)
    ax.set_box_aspect(1)
    ax.plot(e)
    ax.set_ylabel("Error (rad)")
    ax.grid()

    plt.show()
