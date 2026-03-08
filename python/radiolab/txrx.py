from dataclasses import dataclass

import adi
import fir_filter
import matplotlib.pyplot as plt
import modem
import numpy as np
from image_manipulator import image_path, image_to_m_bit


@dataclass
class state:
    theta = 0  # Phase estimate
    integrator = 0  # integrator state


def connect_and_configure_pluto(N, sps=8) -> adi.Pluto:
    """Connect to an Adalm Pluto software defined radio and configure it"""
    sdr = adi.Pluto("usb:")

    # Configure properties
    sdr.rx_rf_bandwidth = 4000000
    sdr.rx_lo = 2000000000
    sdr.tx_lo = 2000000000
    sdr.tx_cyclic_buffer = True
    sdr.tx_hardwaregain_chan0 = -30
    sdr.rx_buffer_size = N * sps
    sdr.gain_control_mode_chan0 = "slow_attack"

    return sdr


def transmit_and_receive(sdr: adi.Pluto, transmit_data: np.ndarray):
    # Read properties
    print("RX LO %s" % (sdr.rx_lo))
    print("TX LO %s" % (sdr.tx_lo))

    # Create a sinewave waveform
    fs = int(sdr.sample_rate)
    print(fs)
    # N = 1024
    # fc = int(3000000 / (fs / N)) * (fs / N)
    # ts = 1 / float(fs)
    # t = np.arange(0, N * ts, ts)
    # i = np.cos(2 * np.pi * t * fc) * 2**14
    # q = np.sin(2 * np.pi * t * fc) * 2**14
    # iq = i + 1j * q
    # data = np.arange(0, N) % 16
    # iq = np.zeros((N,), dtype=complex)
    # for i, t in enumerate(data):
    #     iq[i] = m16_qam.modulate(t)
    # print(iq)

    # iq = np.zeros_like(iq)
    # Send data
    sdr.tx(transmit_data)

    return sdr.rx()
    # Collect data
    # for r in range(20):
    #     x = sdr.rx()
    #     print(x.shape, x)
    #     f, Pxx_den = signal.periodogram(x, fs)
    #     plt.clf()
    #     plt.plot(transmit_data)
    #     plt.plot(x)
    #     # plt.plot(f, 10 * np.log10(Pxx_den))
    #     # plt.ylim([1e-7, 1e2])
    #     # plt.ylim([-100, 10])
    #     # plt.xlabel("frequency [Hz]")
    #     # plt.ylabel("PSD [V**2/Hz]")
    #     # plt.ylabel("PSD [dB/Hz]")
    #     plt.draw()
    #     plt.pause(0.05)
    #     time.sleep(0.1)
    #
    # plt.show()


def main():
    sps = 8

    # Instantiate pulse shaping filter
    rrc = fir_filter.RootRaisedCosine(0.2, 10, sps)
    rrc_coeff = np.array(rrc.get_coefficients())

    M = 4
    qam = modem.Qam(M)
    qpsk = modem.Qam(4)

    # Instantiate Data (Image)
    m_bit_image, img_width, img_height = image_to_m_bit(image_path, M, scale=0.01)
    data = np.astype(m_bit_image.flatten(), int)  # Pure data containing image
    num_symbols = len(data)
    # TODO:
    # Pack data with preamble, barker code etc.

    # Modulate data
    # TODO: Do this better in Cpp
    modulated_data = np.zeros_like(data, dtype=complex)
    for idx, val in enumerate(data):
        modulated_data[idx] = qam.modulate(val)

    # Oversample data
    oversampled_data = np.zeros((num_symbols * sps,), dtype=complex)
    oversampled_data[::sps] = modulated_data

    # Pule shape data
    pulse_shaped_data = np.convolve(oversampled_data, rrc_coeff, mode="same")

    # Send ADC maximum
    pulse_shaped_data *= 2**14

    # Connect to Pluto and configure
    sdr = connect_and_configure_pluto(num_symbols, sps)

    # Transmit and receive one buffer of data
    received_data = transmit_and_receive(sdr, transmit_data=pulse_shaped_data)
    # fs = int(sdr.sample_rate)
    del sdr

    # TODO: Coarse frequency adjustment
    # raised_receive_data = np.pow(received_data, M)
    # Fx = np.fft.fft(raised_receive_data, 256)
    # f = np.fft.fftfreq(256, 1 / fs)
    #
    # fft_peak = np.argmax(Fx)
    # f_peak = fft_peak * fs / M
    # print(fft_peak, f_peak)
    #
    # received_data *= np.exp(-1j * 2 * np.pi * f_peak)

    # Perform matched filtering
    matched_filtered_data = np.convolve(received_data, rrc_coeff, mode="same")

    # Downsample
    # TODO: Do this in a nice way
    # Timing recovery?, Gardner?
    # downsampled_data = np.zeros_like(modulated_data)
    # for byte_idx in range(0, matched_filtered_data.size, sps * 2):
    # plt.plot(matched_filtered_data[byte_idx : byte_idx + sps])
    # plt.show()
    # exit()
    # For now, fetch the sampled data and assume we have perfect sample timing
    matched_filtered_data = matched_filtered_data[::sps]

    k_p = 0.0222
    k_i = 2.4e-4

    e = np.zeros(len(matched_filtered_data))
    theta = np.zeros(len(matched_filtered_data))
    phase_locked_data = np.zeros_like(matched_filtered_data)

    # Normalize for the decoding to work nicely
    matched_filtered_data.real /= np.max(matched_filtered_data.real)
    matched_filtered_data.imag /= np.max(matched_filtered_data.imag)

    # Phase locked loop
    # TODO: implement this in Cpp instead
    for i, x in enumerate(matched_filtered_data):
        x *= np.exp(-1j * state.theta)
        phase_locked_data[i] = x

        # Phase detector
        closest_symbol = qam.modulate(qam.demodulate(x))

        # e[i] = np.imag(x * np.conj(closest_symbol))
        e[i] = np.angle(x * np.conj(closest_symbol))

        # Loop filter
        state.integrator = state.integrator + k_i * e[i]
        state.theta += state.integrator + k_p * e[i]
        theta[i] = state.theta

    plt.figure(tight_layout=True)
    plt.title("Data transmitted and received")
    plt.plot(pulse_shaped_data, label="Transmitted data")
    plt.plot(received_data, label="Received data")
    plt.plot(matched_filtered_data, label="Matched filtered and downsampled")
    plt.legend()

    # Plot constellations of sent and received data
    fig, ax = plt.subplots(2, 2, tight_layout=True)
    ax[0, 0].scatter(pulse_shaped_data.real, pulse_shaped_data.imag)
    ax[0, 0].set_title("Oversampled Pulse shaped data")
    ax[0, 1].scatter(received_data.real, received_data.imag)
    ax[0, 1].set_title("Received data")
    ax[1, 0].scatter(matched_filtered_data.real, matched_filtered_data.imag)
    ax[1, 0].set_title("Matched filtered data")
    ax[1, 1].scatter(phase_locked_data.real, phase_locked_data.imag)
    ax[1, 1].set_title("Phase locked data")

    # Plot PLL error
    fig, ax = plt.subplots(1, 1, tight_layout=True)
    ax.plot(e, label="error")
    ax2 = ax.twinx()
    ax2.plot(theta, label="theta", color="C1")
    ax.set_ylabel("Error (rad)")
    ax2.set_ylabel("Theta (rad)")

    # Decode data
    decoded_data = np.zeros_like(data)
    for idx, val in enumerate(matched_filtered_data):
        decoded_data[idx] = qam.demodulate(val)

    print(f"Original data: {data}")
    print(f"Decoded data: {decoded_data}")

    fig, ax = plt.subplots(3, 1)
    ax[0].set_title("Transmitted image")
    ax[0].imshow(np.reshape(data, (img_height, img_width)), cmap="gray")
    ax[1].set_title("Received image (matched filtered data)")
    ax[1].imshow(np.reshape(decoded_data, (img_height, img_width)), cmap="gray")

    decoded_data = np.zeros_like(data)
    for idx, val in enumerate(phase_locked_data):
        decoded_data[idx] = qam.demodulate(val)

    ax[2].set_title("Received image (phase locked loop data)")
    ax[2].imshow(np.reshape(decoded_data, (img_height, img_width)), cmap="gray")
    plt.show()


main()
