#pragma once

#include <algorithm>
#include <cmath>
#include <complex>
#include <cstdint>
#include <iostream>
#include <vector>

/**
 * @brief does modulation and demodulation initiate with children class
 * @param size is amount of different symbols allowed to to transmit
 * **/
class Modem{
    protected:
        std::vector<std::complex<float>>LUT;

    public:
        int num_of_symbols;

        //modulate a number based on the current modulation settings
        std::complex<float>modulate(uint16_t number_to_modulate);
        
        /**
        * @brief does demodulation corresponding to the children class that instatiated the object
        * @param number_to_demodulate is the the complex number received its then predicted as nerest neigbour
        * **/
        std::uint16_t demodulate(std::complex<float> number_to_demodulate);

        //prints the current look up table in order for debugging
        void print_LUT();
        friend std::ostream &operator<<(std::ostream &os, Modem &modem);
};

/**
 * @brief does MQAM and demodulation
 * @param num_of_symbols is amount of different symbols allowed to to transmit
 * **/
class QAM : public Modem{
    public:
        QAM(int num_of_symbols = 16);
        std::vector<std::complex<float>>generate_LUT(int num_of_symbols);//generates Look Up Table for M-QAM 

};

class PSK:public Modem{
    public:
        PSK(int num_of_symbols = 16);
        std::vector<std::complex<float>>generate_LUT(int num_of_symbols);//generates Look Up Table for M-PSK 
};
