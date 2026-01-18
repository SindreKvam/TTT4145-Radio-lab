
#include "../src/core/fir.h"
#include "../src/core/root_raised_cosine.h"

#include <matplot/matplot.h>

#include <cstdint>
#include <gtest/gtest.h>
#include <iostream>
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

TEST(Core, RootRaisedCosine) {

    int sps = 2; // signals per second
    int span = 12;

    int length = sps * span + 1;
    std::vector<float> time(length, 0.0);

    for (std::uint16_t i = 0; i < length; ++i) {
        time[i] = (i - span * sps / 2.0) / sps;
    }

    RootRaisedCosine rrc_fir1 = RootRaisedCosine(1.0, span, sps);
    std::vector<float> coefficients1 = rrc_fir1.get_coefficients();

    RootRaisedCosine rrc_fir0_5 = RootRaisedCosine(0.5, span, sps);
    std::vector<float> coefficients0_5 = rrc_fir0_5.get_coefficients();

    RootRaisedCosine rrc_fir0_75 = RootRaisedCosine(0.75, span, sps);
    std::vector<float> coefficients0_75 = rrc_fir0_75.get_coefficients();

    auto f = matplot::figure(true);
    matplot::hold("on");
    matplot::stem(time, coefficients1);
    matplot::stem(time, coefficients0_5);
    matplot::stem(time, coefficients0_75);
    matplot::hold("off");
    matplot::legend({"β = 1.0", "β = 0.5", "β = 0.75"});
    matplot::title("Root Raised Cosine impulse response");
    matplot::save("test-artifacts/RRC_Coefficients.svg");
}
