
#include "../src/tx/modulators.h"

#include <matplot/matplot.h>

#include <cstdint>
#include <gtest/gtest.h>
#include <vector>

TEST(TX, QPSK) {

    std::vector<double> polar(2, 0.0);
    std::vector<std::vector<double>> constellation(2, std::vector<double>(8, 0.0));

    for (int i = 0; i < 8; ++i) {
        polar = MPSK(i, 8);

        constellation[0][i] = polar[0];
        constellation[1][i] = polar[1];
    }

    auto f = matplot::figure(true);
    matplot::hold("on");
    matplot::scatter(constellation[0], constellation[1]);
    matplot::title("QPSK Constellation");
    matplot::grid(true);
    matplot::save("test-artifacts/MPSK.svg");
}
