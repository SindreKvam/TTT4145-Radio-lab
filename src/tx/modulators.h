#pragma once

#include <cstdint>
#include <vector>
#include <complex>

std::vector<double> MPSK(uint16_t symbol, uint16_t number_of_symbols);
std::complex<double> MPSK_complex(uint16_t symbol, uint16_t number_of_symbols);
std::complex<double> QPSK_complex(uint16_t symbol);
