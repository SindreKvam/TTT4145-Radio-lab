
#include <cstdint>
#include <stddef.h>
#include <vector>

#include "fir.h"

/**
 * FIR filter instantiation
 **/
Fir::Fir(const std::uint16_t num_taps) { coefficients.resize(num_taps); };

Fir::Fir(const std::vector<float> &taps, const std::uint16_t num_taps)
    : num_taps(num_taps) {

    coefficients.resize(num_taps);

    for (std::uint16_t i = 0; i < num_taps; i++) {
        coefficients[i] = taps[i];
    }
}

/**
 * FIR filter deconstruction
 **/
Fir::~Fir() { coefficients.clear(); }

/**
 * The actual filter implementation
 * \param input The input value
 **/
std::vector<float> Fir::filter(const std::vector<float> &signal) {

    int signal_length = signal.size();
    int output_length = signal_length + num_taps - 1;

    std::vector<float> output(output_length, 0.0);

    for (int i = 0u; i < output_length; ++i) {
        for (int j = 0u; j < num_taps; ++j) {
            if (i - j >= 0 && i - j < signal_length) {
                output[i] += signal[i - j] * coefficients[j];
            }
        }
    }

    return output;
}
