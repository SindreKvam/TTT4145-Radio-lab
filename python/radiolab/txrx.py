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
    agc = 1


def int_to_m_bit_chunks(number, total_bits, chunk_size):
    """
    Converts an integer to a list of m-bit integer chunks.

    Args:
        number (int): The input integer.
        total_bits (int): The total number of bits for the integer (N).
        chunk_size (int): The size of each chunk in bits (M).

    Returns:
        list: A list of integers, each representing an m-bit chunk.
    """
    if total_bits % chunk_size != 0:
        raise ValueError("Total bits must be an exact multiple of the chunk size.")

    # Format the number into a zero-padded binary string of N bits
    binary_string = format(number, f"0{total_bits}b")

    # Split the binary string into chunks of M bits
    chunks = []
    for i in range(0, total_bits, chunk_size):
        chunk_str = binary_string[i : i + chunk_size]
        # Convert each binary chunk string back to an integer
        chunks.append(int(chunk_str, 2))

    return chunks


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
    sdr.gain_control_mode_chan0 = "manual"

    phy = sdr.ctx.find_device("ad9361-phy")
    rx0 = phy.find_channel("voltage0", False)  # False => RX/input channel
    print(list(rx0.attrs.keys()))

    # disable quadrature tracking:
    rx0.attrs["quadrature_tracking_en"] = "0"

    # Disable DC tracking only if needed
    rx0.attrs["rf_dc_offset_tracking_en"].value = "0"
    rx0.attrs["bb_dc_offset_tracking_en"].value = "0"

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
    pll_preamble_length = 1200

    # Instantiate pulse shaping filter
    rrc = fir_filter.RootRaisedCosine(0.2, 10, sps)
    rrc_coeff = np.array(rrc.get_coefficients())

    M = 4
    qam = modem.Qam(M)
    qpsk = modem.Qam(4)

    # ---------- START RX ----------

    # Instantiate Payload (Image)
    m_bit_image, img_width, img_height = image_to_m_bit(image_path, M, scale=0.02)
    payload = np.astype(m_bit_image.flatten(), int)  # Pure data containing image

    # Modulate payload
    # TODO: Do this better in Cpp
    modulated_data = np.zeros_like(payload, dtype=complex)
    for idx, val in enumerate(payload):
        modulated_data[idx] = qam.modulate(val)

    # Include code with nice autocorrelation function
    # https://ntrs.nasa.gov/api/citations/19800017860/downloads/19800017860.pdf
    nasa_32_bit_code = 0x89445BC1
    nasa_36_bit_code = 0xC6859AE80
    nasa_64_bit_code = 0xEC10845E8B3CB0AC
    nasa_code = np.array(
        int_to_m_bit_chunks(nasa_32_bit_code, 32, int(np.log2(M))), dtype=int
    )

    modulated_nasa_code = np.zeros_like(nasa_code, dtype=complex)
    for idx, val in enumerate(nasa_code):
        modulated_nasa_code[idx] = qam.modulate(val)

    # Add preamble for PLL sync
    pll_sync_preamble = np.array(
        [1.0 + 1.0j, -1.0 + 1.0j, -1.0 - 1.0j, 1.0 - 1.0j] * (pll_preamble_length // 4)
    )

    # Create full message to transmit
    print(
        f"Length nasa code: {len(modulated_nasa_code)}, "
        + f"pll preamble: {len(pll_sync_preamble)}, "
        + f"data: {len(modulated_data)}"
    )
    modulated_data = np.concatenate(
        (modulated_nasa_code, pll_sync_preamble, modulated_data)
    )
    num_symbols = len(modulated_data)

    # Oversample data
    oversampled_data = np.zeros((num_symbols * sps,), dtype=complex)
    oversampled_data[::sps] = modulated_data

    # Pulse shape data
    pulse_shaped_data = np.convolve(oversampled_data, rrc_coeff, mode="same")

    # Send ADC maximum
    pulse_shaped_data *= 2**14

    # ---------- END RX ----------

    # Connect to Pluto and configure
    sdr = connect_and_configure_pluto(num_symbols, sps)

    # Transmit and receive one buffer of data
    received_data = transmit_and_receive(sdr, transmit_data=pulse_shaped_data)
    # fs = int(sdr.sample_rate)
    del sdr

    # ---------- START TX ----------

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

    # Find the start of packet by correlating with nasa code
    # Perform the same operations to the code as has been done with the data
    pulse_shaped_code = np.convolve(modulated_nasa_code, rrc_coeff, mode="same")
    matched_filtered_code = np.convolve(pulse_shaped_code, rrc_coeff, mode="same")

    oversampled_code = np.zeros((len(matched_filtered_code) * sps,), dtype=complex)
    oversampled_code[::sps] = matched_filtered_code

    correlation = np.pow(
        np.abs(
            np.correlate(
                matched_filtered_data / np.max(matched_filtered_data),
                oversampled_code,
                mode="same",
            )
        ),
        2,
    )
    # Index of start of data after downsampling
    # start_of_data_index = np.argmax(correlation) // 8 + int(np.log2(M)) - 1
    start_of_data_index = np.argmax(correlation) + sps * (int(np.log2(M)) - 1)
    print(start_of_data_index)

    plt.figure()
    plt.plot(correlation)
    plt.title("Correlation between received data and nasa code")

    matched_filtered_data = np.concatenate(
        (
            matched_filtered_data[start_of_data_index:],
            matched_filtered_data[:start_of_data_index],
        )
    )

    # Remove sync code from the data
    matched_filtered_data = matched_filtered_data[
        len(nasa_code) * sps // 2 : -len(nasa_code) * sps // 2
    ]

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

    # Normalize for the decoding to work nicely
    # TODO: Find a better way of doing this. Equalization?
    # TODO: Add automatic gain control??
    # matched_filtered_data.real /= np.max(matched_filtered_data.real)
    # matched_filtered_data.imag /= np.max(matched_filtered_data.imag)
    matched_filtered_data /= np.max(matched_filtered_data)

    # Rearrange data based on where the start is
    # This only works here, because the transmitter is using a circular buffer
    # Meaning that the data before the beginning of the message, is the end of the
    # previous message (which contains the same data)

    print(
        f"Length after downsample and removed nasa code: {len(matched_filtered_data)}"
    )

    k_p = 0.0222
    k_i = 0.00024

    e = np.zeros(len(matched_filtered_data))
    theta = np.zeros(len(matched_filtered_data))
    phase_locked_data = np.zeros_like(matched_filtered_data)

    # Phase locked loop
    # TODO: implement this in Cpp instead
    for i, x in enumerate(matched_filtered_data):
        x *= np.exp(-1j * state.theta)
        phase_locked_data[i] = x

        # Phase detector
        if i < pll_preamble_length:
            # closest_symbol = qpsk.modulate(qpsk.demodulate(x))
            # Use the fact that we know the preamble
            closest_symbol = pll_sync_preamble[i]
        else:
            closest_symbol = qam.modulate(qam.demodulate(x))

        if i < 10:
            print(x, closest_symbol)

        # e[i] = np.imag(x * np.conj(closest_symbol))
        e[i] = np.angle(x * np.conj(closest_symbol))

        # Loop filter
        state.integrator = state.integrator + k_i * e[i]
        state.theta += state.integrator + k_p * e[i]
        theta[i] = state.theta

    # ---------- END TX ----------

    plt.figure(tight_layout=True)
    plt.title("Data transmitted and received")
    plt.plot(pulse_shaped_data, label="Transmitted data")
    plt.plot(received_data, label="Received data")
    plt.plot(matched_filtered_data, label="Matched filtered and downsampled")
    plt.legend()

    # Plot constellations of sent and received data
    fig, ax = plt.subplots(4, 2, tight_layout=True)
    ax[0, 0].scatter(pulse_shaped_data.real, pulse_shaped_data.imag)
    ax[0, 0].set_title("Oversampled Pulse shaped data")
    ax[0, 1].scatter(received_data.real, received_data.imag)
    ax[0, 1].set_title("Received data")
    ax[1, 0].scatter(matched_filtered_data.real, matched_filtered_data.imag)
    ax[1, 0].set_title("Matched filtered data")
    ax[2, 0].scatter(
        matched_filtered_data[:pll_preamble_length].real,
        matched_filtered_data[:pll_preamble_length].imag,
    )
    ax[2, 0].set_title("Matched filtered data (preamble)")
    ax[2, 1].scatter(
        matched_filtered_data[pll_preamble_length:].real,
        matched_filtered_data[pll_preamble_length:].imag,
    )
    ax[2, 1].set_title("Matched filtered data (payload)")
    ax[1, 1].scatter(phase_locked_data.real, phase_locked_data.imag)
    ax[1, 1].set_title("Phase locked data")
    ax[3, 0].scatter(
        phase_locked_data[:pll_preamble_length].real,
        phase_locked_data[:pll_preamble_length].imag,
    )
    ax[3, 0].set_title("Phase locked data (preamble)")
    ax[3, 1].scatter(
        phase_locked_data[pll_preamble_length:].real,
        phase_locked_data[pll_preamble_length:].imag,
    )
    ax[3, 1].set_title("Phase locked data (payload)")

    # Plot PLL error
    fig, ax = plt.subplots(1, 1, tight_layout=True)
    ax.plot(e, label="error")
    ax.axvline(pll_preamble_length, color="r", label="End of preamble", alpha=0.5)
    ax_t = ax.twinx()
    ax_t.plot(theta, label="theta", color="C1")
    ax.set_ylabel("Error (rad)")
    ax_t.set_ylabel("Theta (rad)")

    matched_filtered_data = matched_filtered_data[pll_preamble_length:]
    phase_locked_data = phase_locked_data[pll_preamble_length:]

    # Decode data
    decoded_data = np.zeros_like(matched_filtered_data, dtype=int)
    for idx, val in enumerate(matched_filtered_data):
        decoded_data[idx] = qam.demodulate(val)

    decoded_pll_data = np.zeros_like(payload)
    for idx, val in enumerate(phase_locked_data):
        decoded_pll_data[idx] = qam.demodulate(val)

    print(f"Original payload: {payload}")
    print(f"Decoded payload: {decoded_data}")
    print(f"Decoded pll payload: {decoded_pll_data}")

    fig, ax = plt.subplots(3, 1, tight_layout=True)
    ax[0].set_title("Transmitted image")
    ax[0].imshow(np.reshape(payload, (img_height, img_width)), cmap="gray")
    ax[1].set_title("Received image (matched filtered data)")
    ax[1].imshow(np.reshape(decoded_data, (img_height, img_width)), cmap="gray")
    ax[2].set_title("Received image (phase locked loop data)")
    ax[2].imshow(np.reshape(decoded_pll_data, (img_height, img_width)), cmap="gray")
    plt.show()


if __name__ == "__main__":
    main()
