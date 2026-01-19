#include <iostream>
#include <random>
#include <vector>
#include <ctime>
#include <cmath>
#include "fault_protection.h"

std::vector<double> MPSK(uint16_t symbol, uint16_t number_of_symbols){
    std::vector<double> I_and_Q(2);
    uint16_t gray_encoding = symbol ^ (symbol >> 1);
    double theta = 2 * M_PI * gray_encoding / number_of_symbols+ M_PI / number_of_symbols;

    I_and_Q[0] = cos(theta);   // I
    I_and_Q[1] = sin(theta);   // Q

    return I_and_Q;
}

int main(){
    std::vector<double>polar = MPSK(0b001,8);
    print_vector(polar);
    polar = MPSK(0b100,8);
    print_vector(polar);
    polar = MPSK(0b000,8);
    print_vector(polar);
}
