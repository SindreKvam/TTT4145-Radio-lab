#pragma once

#include <complex>
#include <vector>

class Pll {
  private:
    float k_p;
    float k_i;

  public:
    explicit Pll(float k_p = 0.0222F, float k_i = 0.00024F);

    std::vector<std::complex<float>>
    phase_lock(const std::vector<std::complex<float>> &signal,
               const std::vector<std::complex<float>> &lut,
               const std::vector<std::complex<float>> &pll_preamble = {}) const;
};
