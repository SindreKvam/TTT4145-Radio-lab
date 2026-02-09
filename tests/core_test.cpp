
#include "../include/config.h"
#include "../src/core/fir.h"
#include "../src/core/modem.h"
#include "../src/core/root_raised_cosine.h"

#include <matplot/matplot.h>

#include <bitset>
#include <cstdint>
#include <gtest/gtest.h>
#include <iostream>
#include <string>
#include <vector>

#define MATPLOT_GENERAL_FONT_SIZE 16
#define MATPLOT_LABEL_SIZE 18

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

TEST(Core, RootRaisedCosineNormalized) {

    int length = RRC_SPS * RRC_SPAN + 1;
    std::vector<float> time(length, 0.0);

    for (std::uint16_t i = 0; i < length; ++i) {
        time[i] = (i - RRC_SPAN * RRC_SPS / 2.0) / RRC_SPS;
    }

    RootRaisedCosine rrc_fir1 = RootRaisedCosine(1.0, RRC_SPAN, RRC_SPS);
    std::vector<float> coefficients1 = rrc_fir1.get_coefficients();
    EXPECT_FLOAT_EQ(1.0f, std::accumulate(coefficients1.begin(),
                                          coefficients1.end(), 0.0f));

    RootRaisedCosine rrc_fir0_5 = RootRaisedCosine(0.5, RRC_SPAN, RRC_SPS);
    std::vector<float> coefficients0_5 = rrc_fir0_5.get_coefficients();
    EXPECT_FLOAT_EQ(1.0f, std::accumulate(coefficients0_5.begin(),
                                          coefficients0_5.end(), 0.0f));

    RootRaisedCosine rrc_fir0_75 = RootRaisedCosine(0.75, RRC_SPAN, RRC_SPS);
    std::vector<float> coefficients0_75 = rrc_fir0_75.get_coefficients();
    EXPECT_FLOAT_EQ(1.0f, std::accumulate(coefficients0_75.begin(),
                                          coefficients0_75.end(), 0.0f));

    auto f = matplot::figure(true);
    matplot::hold("on");
    matplot::stem(time, coefficients1);
    matplot::stem(time, coefficients0_5);
    matplot::stem(time, coefficients0_75);
    matplot::hold("off");
    matplot::legend({"β = 1.0", "β = 0.5", "β = 0.75"});
    matplot::title("Root Raised Cosine impulse response");
    auto ax = matplot::gca();
    ax->font_size(MATPLOT_GENERAL_FONT_SIZE);
    ax->title_font_size_multiplier(1.2);
    ax->x_axis().label_font_size(MATPLOT_LABEL_SIZE);
    ax->y_axis().label_font_size(MATPLOT_LABEL_SIZE);
    ax->position({0.15, 0.15, 0.75, 0.70});
    matplot::save("test-artifacts/RRC_Coefficients.svg");
}

TEST(Core, MQamModulation) {

    std::vector<std::complex<double>> symbols(16, 0.0 + 1j * 0.0);
    std::vector<std::vector<double>> constellation(
        2, std::vector<double>(16, 0.0));

    Mqam mqam = Mqam(16);

    for (uint16_t i = 0; i < 16; ++i) {
        symbols[i] = mqam.modulate(i);

        // Check that the lengths are normalized
        EXPECT_LE(std::abs(symbols[i]), 1.0);

        constellation[0][i] = symbols[i].real();
        constellation[1][i] = symbols[i].imag();
    }

    auto fig = matplot::figure(true);
    auto ax = matplot::gca();
    ax->font_size(MATPLOT_GENERAL_FONT_SIZE);
    ax->title_font_size_multiplier(1.2);
    ax->x_axis().label_font_size(MATPLOT_LABEL_SIZE);
    ax->y_axis().label_font_size(MATPLOT_LABEL_SIZE);
    ax->position(
        {0.15, 0.15, 0.75, 0.70}); // Title gets removed if we dont do this
    matplot::hold("on");
    matplot::scatter(constellation[0], constellation[1]);
    for (int i = 0; i < 16; ++i) {
        matplot::text(constellation[0][i] + 0.04, constellation[1][i] + 0.04,
                      std::bitset<4>(i).to_string())
            ->font_size(14)
            .color("blue");
    }
    ax->title("16-QAM Constellation");
    matplot::xlim({-1.0, 1.0});
    matplot::ylim({-1.0, 1.0});
    matplot::grid(true);
    matplot::ylabel("Quadrature (Q)");
    matplot::xlabel("In-phase (I)");
    matplot::save("test-artifacts/16-QAM.svg");
}

TEST(Core, MQamDemodulation) {

    Mqam mqam = Mqam(16);

    std::complex<float> sample(1.0, 1.0);

    EXPECT_EQ(mqam.demodulate(sample), 2);
}

TEST(Core, MQamModem) {

    Mqam mqam = Mqam(16);

    for (uint16_t i = 0; i < 16; ++i) {
        EXPECT_EQ(mqam.demodulate(mqam.modulate(i)), i);
    }
}
