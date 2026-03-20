import time
from dataclasses import dataclass

import adi
import cv2
import fir_filter
import matplotlib.pyplot as plt
import modem
import numpy as np
import scipy
from app.sources import array_image_to_m_bit, image_path, image_to_m_bit
from phy.rx import ModemRx
from phy.tx import ModemTx
from radio import connect_and_configure_pluto
from tx import get_pll_preamble


@dataclass
class state:
    theta = 0  # Phase estimate
    integrator = 0  # integrator state
    agc = 1


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

    time.sleep(1)

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
    M = 4
    threshold = 1000 / np.log2(M)
    sps = 8
    pll_preamble_length = 600

    # Instantiate pulse shaping filter
    rrc = fir_filter.RootRaisedCosine(0.2, 10, sps)
    rrc_coeff = np.array(rrc.get_coefficients())
    filter_state = scipy.signal.lfiltic(rrc_coeff, 1, 0)

    # Instantiate modem
    qam = modem.Qam(M)

    # Instantiate Payload (Image)
    video_capture = True

    if video_capture:
        cap = cv2.VideoCapture(0)
        ret, img = cap.read()
        m_bit_image, img_width, img_height = array_image_to_m_bit(
            img[:, :, 1], M, scale=0.2
        )
        payload = np.astype(m_bit_image.flatten(), int)

    else:
        m_bit_image, img_width, img_height = image_to_m_bit(image_path, M, scale=0.02)
        payload = np.astype(m_bit_image.flatten(), int)  # Pure data containing image

    plt.figure()
    plt.imshow(np.reshape(payload, (img_height, img_width)), cmap="gray")
    plt.show()

    # ---------- START TX ----------
    tx_modem = ModemTx(qam, sps, rrc_coeff)

    modulated_payload = tx_modem.modulate_payload(payload)
    payload_with_preamble = tx_modem.add_pll_preamble(
        modulated_payload, preamble_length=pll_preamble_length
    )
    modulated_data = tx_modem.add_modulated_codeword(payload_with_preamble, 64)

    num_symbols = len(modulated_data)

    oversampled_data = tx_modem.upsample(modulated_data)
    pulse_shaped_data = tx_modem.pulse_shape(oversampled_data)

    # Send ADC maximum
    pulse_shaped_data *= 2**14

    # ---------- END TX ----------
    # ---------- START HW ----------

    # Connect to Pluto and configure
    sdr = connect_and_configure_pluto(
        num_symbols,
        rx_lo=2_400_000_000,
        tx_lo=2_400_000_000,
        sps=sps,
        tx_cyclic_buffer=True,
    )

    # Transmit and receive one buffer of data
    received_data = transmit_and_receive(sdr, transmit_data=pulse_shaped_data)
    # fs = int(sdr.sample_rate)
    del sdr

    # ---------- END HW ----------
    # ---------- START RX ----------

    rx_modem = ModemRx(qam, sps, rrc_coeff)

    matched_filtered_data = rx_modem.matched_filtering(received_data)

    # TODO: Coarse frequency adjustment
    # raised_receive_data = np.pow(received_data, M)
    # Fx = np.fft.fft(raised_receive_data, 256)
    # f = np.fft.fftfreq(256, 1 / fs)
    #
    # fft_peak = np.argmax(np.abs(Fx))
    # f_peak = fft_peak * fs / 256
    # print(fft_peak, f_peak)
    #
    # received_data *= np.exp(-1j * 2 * np.pi * f_peak)
    #
    # plt.plot(f, np.abs(Fx))
    # plt.show()

    # get the codeword and do pulse shaping and matched filtering on it
    modulated_code = tx_modem.modulate_payload(tx_modem._get_codeword(64))
    pulse_shaped_code = np.convolve(modulated_code, rrc_coeff, mode="same")
    matched_filtered_code = np.convolve(pulse_shaped_code, rrc_coeff, mode="same")

    # Recover timing
    matched_filtered_data = rx_modem.recover_timing(matched_filtered_data)

    correlation = np.pow(
        np.abs(
            np.correlate(
                matched_filtered_data / np.max(matched_filtered_data),
                matched_filtered_code,
                mode="same",
            )
        ),
        2,
    )

    plt.figure()
    plt.plot(correlation)
    plt.title("Correlation")
    plt.show()

    try:
        start_of_data_index = rx_modem.detect_codeword(
            matched_filtered_data, matched_filtered_code, threshold=threshold
        )[0]
    except IndexError:
        print("Error, no start of packet found")
        exit()

    # Remove sync code from the data
    matched_filtered_data = rx_modem.remove_codeword(
        matched_filtered_data, start_of_data_index, len(modulated_code)
    )

    # TODO, replace this with AGC?
    matched_filtered_data /= np.max(matched_filtered_data)

    pll_preamble = get_pll_preamble(pll_preamble_length)
    phase_locked_data = rx_modem.phase_locked_loop(matched_filtered_data, pll_preamble)

    # ---------- END RX ----------

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
    # fig, ax = plt.subplots(1, 1, tight_layout=True)
    # ax.plot(e, label="error")
    # ax.axvline(pll_preamble_length, color="r", label="End of preamble", alpha=0.5)
    # ax_t = ax.twinx()
    # ax_t.plot(theta, label="theta", color="C1")
    # ax.set_ylabel("Error (rad)")
    # ax_t.set_ylabel("Theta (rad)")

    matched_filtered_data = matched_filtered_data[pll_preamble_length:]
    phase_locked_data = phase_locked_data[pll_preamble_length:]

    # Decode data
    decoded_data = np.zeros_like(payload)
    for idx, val in enumerate(matched_filtered_data):
        if idx >= len(payload):
            break
        decoded_data[idx] = qam.demodulate(val)

    decoded_pll_data = np.zeros_like(payload)
    for idx, val in enumerate(phase_locked_data):
        if idx >= len(payload):
            break
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
