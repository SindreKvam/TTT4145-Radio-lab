#pragma once

#include <cstdint>
#include <vector>

class Fir {
  public:
    Fir(const std::uint16_t num_taps);
    Fir(const std::vector<float> &coefficients, const std::uint16_t num_taps);
    ~Fir();

    std::vector<float> filter(const std::vector<float> &signal);
    std::vector<float> get_coefficients() { return coefficients; };

  protected:
    std::vector<float> coefficients;
    std::uint16_t num_taps;
    std::vector<float> delay_line;
};
