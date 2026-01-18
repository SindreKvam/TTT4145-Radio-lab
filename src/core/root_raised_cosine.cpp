
#define _USE_MATH_DEFINES

#include "root_raised_cosine.h"
#include "fir.h"

#include <cmath>
#include <cstdint>
#include <numeric>
#include <vector>

/**
 * \param beta The roll-off factor.
 * \param span The length of the filter in symbols.
 * \param sps The symbol rate.
 **/
RootRaisedCosine::RootRaisedCosine(float beta, int span, int sps)
    : Fir(span * sps + 1) {

    double T_s = 1.0 / sps;

    for (std::uint16_t i = 0; i < num_taps; ++i) {
        double time = (i - span * sps / 2.0) * T_s;

        // There are three cases in the impulse response
        // of the Root Raised Cosine filter
        // See https://en.wikipedia.org/wiki/Root-raised-cosine_filter

        // Main tap at t=0
        if (std::abs(time) < 1e-9) {
            coefficients[i] = sps * (1 + beta * (4 / M_PI - 1));
        }
        // Handle points where the denominator is zero
        else if (std::abs(std::abs(time) - T_s / (4 * beta)) < 1e-9 &&
                 std::abs(beta) > 1e-9) {
            coefficients[i] = (sps * beta / std::sqrt(2)) *
                              ((1 + 2 / M_PI) * std::sin(M_PI / (4 * beta)) +
                               (1 - 2 / M_PI) * std::cos(M_PI / (4 * beta)));
        }
        // Otherwise
        else {

            coefficients[i] =
                sps *
                (std::sin(M_PI * sps * time * (1 - beta)) +
                 4 * beta * time * sps *
                     std::cos(M_PI * sps * time * (1 + beta))) /
                (M_PI * time * sps * (1 - std::pow(4 * beta * time * sps, 2)));
        }

        // Normalize the coefficients
        // double sum_coeff =
        //     std::accumulate(coefficients.begin(), coefficients.end(), 0.0);
        //
        // for (std::uint16_t i = 0; i < num_taps; ++i) {
        //     coefficients[i] /= sum_coeff;
        // }
    }
}

RootRaisedCosine::~RootRaisedCosine() {}
