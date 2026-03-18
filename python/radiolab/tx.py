"""This module contains all methods needed to generate a data package
and to be ready for transmitting data"""

import time

import adi
import fir_filter
import modem
import numpy as np
from app.sources import image_path, image_to_m_bit
from radio import connect_and_configure_pluto


def int_to_m_bit_chunks(number, total_bits, chunk_size) -> np.ndarray:
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

    return np.array(chunks, dtype=int)


def get_modulated_codeword(
    qam: modem.Qam, num_bits: int = 32, modulation: int = 4
) -> np.ndarray:
    """Provide a code-word with nice autocorrelation properties.
    Only a few selected codewords from
    https://ntrs.nasa.gov/api/citations/19800017860/downloads/19800017860.pdf
    is implemented here.
    """

    match num_bits:
        case 32:
            codeword = 0x89445BC1
        case 36:
            codeword = 0xC6859AE80
        case 64:
            codeword = 0xEC10845E8B3CB0AC
        case _:
            raise ValueError(f"Codeword with {num_bits} have not been configured")

    code = int_to_m_bit_chunks(codeword, num_bits, int(np.log2(modulation)))

    modulated_nasa_code = np.zeros_like(code, dtype=complex)
    for idx, val in enumerate(code):
        modulated_nasa_code[idx] = qam.modulate(val)

    return modulated_nasa_code


def get_pll_preamble(pll_preamble_length: int = 1200):
    pll_sync_preamble = np.array(
        [1.0 + 1.0j, -1.0 + 1.0j, -1.0 - 1.0j, 1.0 - 1.0j] * (pll_preamble_length // 4)
    )

    return pll_sync_preamble


def oversample_data(data: np.ndarray, oversample_factor: int):
    oversampled_data = np.zeros_like(data, shape=(len(data) * oversample_factor,))
    oversampled_data[::oversample_factor] = data
    return oversampled_data


def tx_main(sdr: adi.Pluto, transmit_data: np.ndarray):
    """Method for continuously transmit images"""

    while True:
        """Main loop"""

        sdr.tx(transmit_data)

        print("transmitting")
        time.sleep(0.1)


if __name__ == "__main__":
    M = 4
    sps = 8
    rrc = fir_filter.RootRaisedCosine(0.2, 10, sps)

    rrc_coeff = rrc.get_coefficients()

    qam = modem.Qam(M)
    modulated_code = get_modulated_codeword(qam)
    pll_preamble = get_pll_preamble()

    preamble = np.concatenate((modulated_code, pll_preamble))

    oversampled_preamble = oversample_data(preamble, sps)

    m_bit_image, img_width, img_height = image_to_m_bit(image_path, M, scale=0.02)
    payload = np.astype(m_bit_image.flatten(), int)  # Pure data containing image

    modulated_payload = np.zeros_like(payload, dtype=complex)
    for idx, val in enumerate(payload):
        modulated_payload[idx] = qam.modulate(val)

    oversampled_payload = oversample_data(modulated_payload, sps)

    data = np.concatenate((oversampled_preamble, oversampled_payload))
    pulse_shaped_data = np.convolve(data, rrc_coeff, mode="same")
    print(np.max(pulse_shaped_data.real))
    print(np.max(pulse_shaped_data.imag))
    pulse_shaped_data *= 2**14

    data_length = pulse_shaped_data.size

    sdr = connect_and_configure_pluto(data_length, sps=8)

    tx_main(sdr, pulse_shaped_data)
