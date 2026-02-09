#include "modem.h"

Mqam::Mqam(uint8_t size) {
    generate_constellation(size);
    generate_lookup_table(size);
}

/**
 * @brief Construct the M-QAM constellation diagram.
 */
void Mqam::generate_constellation(uint8_t size) {

    if (std::sqrt(size) != static_cast<int>(std::sqrt(size))) {
        throw std::runtime_error("M-QAM size must be square");
    }

    // Generate constellation diagram
    // Method based on python gray_code_generator script
    for (int i = 0; i < (int)std::sqrt(size); ++i) {
        int gray_code = i ^ (i >> 1);
        int vertical_gray_code = gray_code << (int)std::log2(size) / 2;

        constellation[i][0] = gray_code;
        constellation[0][i] = vertical_gray_code;
    }

    for (int i = 1; i < (int)std::sqrt(size); ++i) {
        for (int j = 1; j < (int)std::sqrt(size); ++j) {
            constellation[i][j] = constellation[i][0] + constellation[0][j];
        }
    }
}

void Mqam::generate_lookup_table(uint8_t size) {

    int shift = (std::sqrt(size) - 1);
    float real_val;
    float imag_val;

    for (int x_pos = 0; x_pos < constellation.size(); ++x_pos) {
        for (int y_pos = 0; y_pos < constellation[x_pos].size(); ++y_pos) {

            int symbol = constellation[x_pos][y_pos];

            std::complex<float> modulation;
            real_val = x_pos * 2 - shift; // some sick mapping getting centre at
                                          // 0 and peaks at sqrt(M)-1
            imag_val = y_pos * 2 - shift;

            float normalized_real = real_val / (std::sqrt(size) - 1);
            float normalized_imag = -imag_val / (std::sqrt(size) - 1);

            modulation.real(normalized_real);
            modulation.imag(normalized_imag);

            float scale = M_SQRT1_2f;

            lookup_table[symbol] = scale * modulation;
        }
    }
}
