#include <algorithm>
#include <cmath>
#include <complex>
#include <iostream>
#include <vector>

// these are for testing
#include <ctime>
#include <random>

#include "modem.h"

std::vector<std::complex<float>> QAM::generate_LUT(int num_of_symbols) {

    std::vector<std::complex<float>> LUT(num_of_symbols);
    // makes a 2d vector
    std::vector<std::vector<int>> graycode_grid(
        static_cast<int>(std::sqrt(num_of_symbols)),
        std::vector<int>(static_cast<int>(std::sqrt(num_of_symbols))));

    std::vector<int> horisontal_gray_codes(std::sqrt(num_of_symbols));
    std::vector<int> vertical_gray_codes(std::sqrt(num_of_symbols));

    // used for later mapping
    int shift = (std::sqrt(num_of_symbols) - 1);
    int shifted_real;
    int shifted_imag;
    double normalized_real;
    double normalized_imag;

    // creates horisontal gray codes
    for (int i = 1; i < std::sqrt(num_of_symbols); i++) {
        horisontal_gray_codes[i] = i ^ (i >> 1);
    }

    vertical_gray_codes = horisontal_gray_codes;
    // shiftoperation to all elements in array to the left
    std::transform(vertical_gray_codes.begin(), vertical_gray_codes.end(),
                   vertical_gray_codes.begin(), [num_of_symbols](int x) {
                       return x << static_cast<int>(std::log2(num_of_symbols)) /
                                       2;
                   });

    for (int i = 0; i < vertical_gray_codes.size(); i++) {
        for (int j = 0; j < horisontal_gray_codes.size(); j++) {
            graycode_grid[i][j] =
                vertical_gray_codes[i] ^ horisontal_gray_codes[j];

            // Mapping to get centre at 0 and peaks at sqrt(M)-1
            shifted_imag = i * 2 - shift;
            shifted_real = j * 2 - shift;

            normalized_real = shifted_real / (std::sqrt(num_of_symbols) - 1);
            normalized_imag = -shifted_imag / (std::sqrt(num_of_symbols) - 1);

            LUT[graycode_grid[i][j]] =
                std::complex<float>(normalized_real, normalized_imag);
        }
    }

    return LUT;
}

std::vector<std::complex<float>> PSK::generate_LUT(int num_of_symbols) {

    std::vector<std::complex<float>> LUT(num_of_symbols);

    for (int i = 0; i < num_of_symbols; i++) {
        std::vector<double> I_and_Q(2);
        uint16_t gray_encoding = i ^ (i >> 1);

        double theta =
            2 * M_PI * gray_encoding / num_of_symbols + M_PI / num_of_symbols;

        std::complex<float> IQ_complex =
            static_cast<std::complex<float>>(std::polar(1., theta));

        LUT[i] = IQ_complex;
    }

    return LUT;
}

// instantiate the modulators
QAM::QAM(int num_of_symbols) {
    this->num_of_symbols = num_of_symbols;
    this->LUT = generate_LUT(num_of_symbols);
}

PSK::PSK(int num_of_symbols) {
    this->num_of_symbols = num_of_symbols;
    this->LUT = generate_LUT(num_of_symbols);
}

// modulate a number based on the current modulation settings
std::complex<float> Modem::modulate(uint16_t number_to_modulate) {
    return LUT[number_to_modulate];
}

uint16_t Modem::demodulate(std::complex<float> number_to_demodulate) {
    uint16_t closest_index;
    float smallest_error = 2;
    float new_error;

    // cant ficure out a faster way unfortunatly
    for (int i = 0; i < LUT.size(); i++) {
        new_error = std::abs(LUT[i] - number_to_demodulate);
        if (new_error < smallest_error) {
            smallest_error = new_error;
            closest_index = i;
        }
    }
    return closest_index;
}

// prints the current look up table in order for debugging
void Modem::print_LUT() {
    for (int i = 0; i < LUT.size(); i++) {
        std::cout << "index " << i << " in LUT is " << LUT[i] << std::endl;
    }
}

std::ostream &operator<<(std::ostream &os, Modem &modem) {
    for (int i = 0; i < modem.LUT.size(); i++) {
        std::cout << "index " << i << " in LUT is " << modem.LUT[i]
                  << std::endl;
    }
    return os;
}

// int main(){
//     int mod_size = 16;
//     QAM QAM_16(mod_size);
//     PSK PSK_16(mod_size);

//     //noise generation
//     unsigned int random_number = static_cast<unsigned int>(time(NULL));
//     float mean = 0;
//     float st_dev = 1/(2*(std::sqrt(mod_size)-1));

//     std::srand(time(0));
//     std::mt19937 gen(random_number);
//     std::normal_distribution<float> distribution(mean, st_dev);

//     for(int i = 0; i < mod_size; i++){
//         std::complex<float> modulation = QAM_16.modulate(i);
//         std::complex<float> noisy_modulation = modulation;

//         noisy_modulation.real(noisy_modulation.real() + distribution(gen));
//         noisy_modulation.imag(noisy_modulation.imag() + distribution(gen));

//         uint16_t ret = QAM_16.demodulate(noisy_modulation);
//         std::cout <<"given val = "<< i << " returned val = " << ret << "" <<
//         std::endl;
//     }

// }
