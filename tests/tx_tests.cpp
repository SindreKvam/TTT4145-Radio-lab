
#include "../src/modem/modem.h"
#include "tests.h"

#include "gtest/gtest.h"
#include <matplot/matplot.h>

#include <cstdint>
#include <gtest/gtest.h>
#include <string>
#include <vector>

// Allow parameterization of tests
class MQamModulationTestFixture : public ::testing::TestWithParam<int> {
  protected:
    QAM mqam;
};

TEST_P(MQamModulationTestFixture, MQamModulation) {

    const int M = GetParam();

    std::vector<std::complex<float>> symbols(M, 0.0 + 1j * 0.0);
    std::vector<std::vector<double>> constellation(2,
                                                   std::vector<double>(M, 0.0));

    QAM mqam(M);
    const int bits_per_symbol = static_cast<int>(std::log2(M));

    for (uint16_t i = 0; i < mqam.num_of_symbols; ++i) {
        symbols[i] = mqam.modulate(i);

        // Check that the lengths are normalized
        EXPECT_LE(std::abs(symbols[i].real()), 1.0);
        EXPECT_LE(std::abs(symbols[i].imag()), 1.0);

        constellation[0][i] = symbols[i].real();
        constellation[1][i] = symbols[i].imag();
    }

    // Create figure and configure font size etc
    auto fig = generate_figure();

    // Add scatter points
    matplot::scatter(constellation[0], constellation[1]);
    for (int i = 0; i < mqam.num_of_symbols; ++i) {
        matplot::text(constellation[0][i] + 0.04, constellation[1][i] + 0.04,
                      std::to_string(i))
            ->font_size(14)
            .color("blue");
    }

    // Add title, labels etc.
    matplot::title(std::to_string(mqam.num_of_symbols) + "-QAM Constellation");
    matplot::xlim({-1.5, 1.5});
    matplot::ylim({-1.5, 1.5});
    matplot::ylabel("Quadrature (Q)");
    matplot::xlabel("In-phase (I)");
    matplot::grid(true);
    matplot::save("test-artifacts/" + std::to_string(mqam.num_of_symbols) +
                  "-QAM.svg");
}

// Run testcase with multiple different parameter values
INSTANTIATE_TEST_CASE_P(MQamModulationTests, MQamModulationTestFixture,
                        ::testing::Values(4, 16, 64, 256, 1024));

TEST(Modem, MQamDemodulation) {

    QAM mqam = QAM(16);

    std::complex<float> sample(1.0, 1.0);

    EXPECT_EQ(mqam.demodulate(sample), 2);
}

TEST(Modem, MQamModem) {

    QAM mqam = QAM(16);

    for (uint16_t i = 0; i < 16; ++i) {
        EXPECT_EQ(mqam.demodulate(mqam.modulate(i)), i);
    }
}
