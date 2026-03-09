import matplotlib.pyplot as plt
import numpy as np
from qpsk_modulation import QPSK


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


def preamble_detector(data: np.ndarray, preamble_code: np.ndarray):
    """"""

    return np.correlate(data, preamble_code, mode="full")


def main():
    nasa_32_bit_code = 0x89445BC1

    M = 4

    payload = np.random.randint(0, M, 1000, dtype="int")
    payload_start, payload_end = np.array_split(payload, int(np.log2(M)))

    code32_bit = np.array(
        int_to_m_bit_chunks(nasa_32_bit_code, 32, int(np.log2(M))), dtype=int
    )

    modulated_code32_bit = QPSK(code32_bit)

    data = np.concatenate((payload_start, code32_bit, payload_end))
    modulated_data = QPSK(data)

    print(len(payload_start), len(code32_bit), len(payload_end), len(data))

    convolution = preamble_detector(modulated_data, modulated_code32_bit)
    codeword_index = np.argmax(convolution)
    start_of_data = codeword_index + int(np.log2(M)) - 1
    print(f"codeword index: {codeword_index}")
    print(f"Length of data after index: {len(modulated_data[start_of_data:])}")

    plt.title("Autocorrelation")
    plt.plot(
        np.abs(preamble_detector(modulated_code32_bit, modulated_code32_bit)) ** 2,
        label=hex(nasa_32_bit_code),
    )
    plt.legend()
    plt.figure()
    plt.plot(convolution, label="Correlation of data and code")
    plt.xlabel("Lag")
    plt.legend()
    plt.show()


if __name__ == "__main__":
    main()
