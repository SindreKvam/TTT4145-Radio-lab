#pragma once

#include <iostream>
#include <vector>
#include <cmath>
#include <complex>
#include <algorithm>


/**
 * @brief does modulation
 * @param size is amount of different symbols allowed to to transmit
 * **/
class Modulator{
    private:

        std::vector<std::complex<float>>LUT;
        std::vector<std::complex<float>>generate_LUT(int size);//generates Look Up Table for M-QAM 

    public:
        int num_of_symbols;
        std::string mod_scheme;
        
        //instantiate the modulator
        Modulator(std::string mod_scheme = "QAM", int num_of_symbols = 16);

        //modulate a number based on the current modulation settings
        std::complex<float>modulate(uint16_t number_to_modulate);

        //prints the current look up table in order for debugging
        void print_LUT();
};
