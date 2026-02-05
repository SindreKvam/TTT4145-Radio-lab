
#include <cstdint>
#include <stddef.h>
#include <vector>

#include "fir.h"

/**
 * FIR filter instantiation
 **/
Fir::Fir(const std::uint16_t num_taps) : num_taps(num_taps) {
    coefficients.resize(num_taps);
    delay_line.assign(num_taps - 1, 0.0f);
};

Fir::Fir(const std::vector<float> &taps, const std::uint16_t num_taps)
    : num_taps(num_taps) {

    coefficients.resize(num_taps);
    delay_line.assign(num_taps - 1, 0.0f);

    for (std::uint16_t i = 0; i < num_taps; i++) {
        coefficients[i] = taps[i];
    }
}

/**
 * FIR filter deconstruction
 **/
Fir::~Fir() {
    coefficients.clear();
    delay_line.clear();
}

/**
 * The actual filter implementation
 * input N samples -> output N samples.
 **/
std::vector<float> Fir::filter(const std::vector<float> &signal) {
    size_t signal_length = signal.size();
    std::vector<float> output(signal_length, 0.0f);

    // Perform convolution
    for (size_t i = 0; i < signal_length; ++i) {
        float acc = 0.0f;
        for (size_t j = 0; j < num_taps; ++j) {
            // Index into the combined [delay_line, signal]
            int idx = static_cast<int>(i) - static_cast<int>(j);

            // If index is positive, fetch from the signal
            if (idx >= 0) {
                acc += signal[idx] * coefficients[j];
            } else {
                // If index is negative, we use the last values from the
                // previous signal (delay line)
                // Update mapping since cpp does not support negative indexing
                int delay_idx = static_cast<int>(delay_line.size()) + idx;
                if (delay_idx >= 0) {
                    acc += delay_line[delay_idx] * coefficients[j];
                }
            }
        }
        output[i] = acc;
    }

    // Update delay line with the tail of the current signal
    if (num_taps > 1) {
        size_t to_copy = std::min(signal_length, delay_line.size());
        size_t offset = delay_line.size() - to_copy;

        // Shift old samples left
        if (offset > 0) {
            std::move(delay_line.begin() + to_copy, delay_line.end(),
                      delay_line.begin());
        }

        // Copy new samples to the end
        std::copy(signal.end() - to_copy, signal.end(),
                  delay_line.begin() + offset);
    }

    return output;
}
