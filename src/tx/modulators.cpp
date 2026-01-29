#include <iostream>
#include <random>
#include <vector>
#include <ctime>
#include <cmath>
#include "fault_protection.h"
#include <complex>
#include <fstream>


std::vector<double> MPSK(uint16_t symbol, uint16_t number_of_symbols){
    std::vector<double> I_and_Q(2);
    uint16_t gray_encoding = symbol ^ (symbol >> 1);
    double theta = 2 * M_PI * gray_encoding / number_of_symbols+ M_PI / number_of_symbols;

    I_and_Q[0] = cos(theta);   // I
    I_and_Q[1] = sin(theta);   // Q

    return I_and_Q;
}

std::complex<double> MPSK_complex(uint16_t symbol, uint16_t number_of_symbols){
    std::vector<double> I_and_Q(2);
    uint16_t gray_encoding = symbol ^ (symbol >> 1);
    double theta = 2 * M_PI * gray_encoding / number_of_symbols+ M_PI / number_of_symbols;

    std::complex<double> IQ_complex = std::polar(1.,theta);
    return IQ_complex;
}

std::complex<double> QPSK_complex(uint16_t symbol, uint16_t number_of_symbols = 16){
    std::complex<double> modulation;
    std::fstream csv("gray_codes/graycodes.csv", std::ios::in);

    std::vector<std::vector<std::string>>LUT(number_of_symbols, std::vector<std::string>(3));

    std::string line;
    std::string num;
    int iterator = 0;
    int iterator_2 = 0;

    while (std::getline(csv, line)) {
        std::stringstream ss(line);
        std::vector<std::string> row(3);

        for (int i = 0; i < 3 && std::getline(ss, num, ','); ++i) {
            row[i] = num;
        }

        LUT.push_back(row);
    }

    for (std::vector<std::string> symbol: LUT){
        std::cout<<symbol[0]<<' '<<symbol[1]<<' '<<symbol[2]<<std::endl;
    }

    return 0;
}



// int main(){
//     //std::cout<<MPSK_complex(0101, 16)<<std::endl;
//     QPSK_complex(8);
// }
