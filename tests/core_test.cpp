
#include "../src/core/fir.h"
#include <cstdint>
#include <gtest/gtest.h>
#include <vector>

TEST(Core, FirFilter) {

    unsigned int num_taps = 15;

    Fir fir_filter = Fir(num_taps);
    std::vector<float> coefficients = fir_filter.get_coefficients();

    // Check if number of coefficients match
    EXPECT_EQ(coefficients.size(), num_taps);
    for (float coeff : coefficients) {
        EXPECT_EQ(coeff, 0.0);
    }
}

TEST(Core, CustomFirFilter) {

    std::uint16_t num_taps = 9;
    std::vector<float> taps = {1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0};

    Fir fir_filter = Fir(taps, num_taps);
    std::vector<float> coefficients = fir_filter.get_coefficients();

    EXPECT_EQ(taps.size(), coefficients.size());
    for (std::uint16_t i = 0; i < num_taps; ++i) {
        EXPECT_EQ(taps[i], coefficients[i]);
    }
}

TEST(Core, FirFilterConvolution) {

    std::uint16_t num_taps = 3;
    std::vector<float> taps = {1.0, 0.0, -1.0};

    Fir fir_filter = Fir(taps, num_taps);

    std::vector<float> signal = {5.0, 6.0, 7.0, 8.0, 9.0};

    std::vector<float> output = fir_filter.filter(signal);
    std::vector<float> expected_output = {5.0, 6.0, 2.0, 2.0, 2.0, -8.0, -9.0};

    EXPECT_EQ(output.size(), expected_output.size());
    for (std::uint16_t i = 0; i < output.size(); ++i) {
        EXPECT_EQ(output[i], expected_output[i]);
    }
}
