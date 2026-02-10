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
    protected:
        std::vector<std::complex<float>>LUT;

    public:
        int num_of_symbols;

        //modulate a number based on the current modulation settings
        std::complex<float>modulate(uint16_t number_to_modulate);

        //prints the current look up table in order for debugging
        void print_LUT();
};

class QAM : public Modulator{
    public:
        QAM(int num_of_symbols = 16);
        std::vector<std::complex<float>>generate_LUT(int num_of_symbols);//generates Look Up Table for M-QAM 

};

class PSK:public Modulator{
    public:
        PSK(int num_of_symbols = 16);
        std::vector<std::complex<float>>generate_LUT(int num_of_symbols);//generates Look Up Table for M-PSK 

};
