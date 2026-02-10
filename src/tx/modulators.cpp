#include <iostream>
#include <vector>
#include <cmath>
#include <complex>
#include <algorithm>

#include "modulators.h"


    
std::vector<std::complex<float>> QAM::generate_LUT(int num_of_symbols){//generates Look Up Table for M-QAM

    std::vector<std::complex<float>>LUT(num_of_symbols);    
    //makes a 2d vector
    std::vector<std::vector<int>>graycode_grid(static_cast<int>(std::sqrt(num_of_symbols)),std::vector<int>(static_cast<int>(std::sqrt(num_of_symbols)))); 
    std::vector<int> horisontal_gray_codes(std::sqrt(num_of_symbols));
    std::vector<int> vertical_gray_codes(std::sqrt(num_of_symbols));

    //used for later mapping
    int shift = (std::sqrt(num_of_symbols)-1);
    int shifted_real;
    int shifted_imag;
    double normalized_real;
    double normalized_imag;

    //creates horisontal gray codes
    for (int i = 1; i < std::sqrt(num_of_symbols); i++){
        horisontal_gray_codes[i] = i ^ (i >> 1); 
    }

    vertical_gray_codes = horisontal_gray_codes;
    //shiftoperation to all elements in array to the left
    std::transform(vertical_gray_codes.begin(), vertical_gray_codes.end(), vertical_gray_codes.begin(),
    [num_of_symbols](int x){return x << static_cast<int>(std::log2(num_of_symbols)) / 2;});

    
    for (int i = 0; i < vertical_gray_codes.size(); i++){
        for (int j = 0; j < horisontal_gray_codes.size(); j++){
            graycode_grid[i][j] = vertical_gray_codes[i] ^ horisontal_gray_codes[j];// just for visualization

            shifted_imag = i*2 - shift;//some sick mappping getting centre at 0 and peaks at sqrt(M)-1
            shifted_real = j*2 - shift;

            normalized_real = shifted_real/(std::sqrt(num_of_symbols) - 1);
            normalized_imag = -shifted_imag/(std::sqrt(num_of_symbols) - 1);//minus just to correspond with sketch
        
            LUT[graycode_grid[i][j]] = std::complex<float>(normalized_real,normalized_imag);
        }
    }
    //only for visualisation
    // for (int i = 0; i < vertical_gray_codes.size(); i++){
    //     for (int j = 0; j < horisontal_gray_codes.size(); j++){
    //         std::cout<<graycode_grid[i][j]<<" ";
    //     }
    //     std::cout<<std::endl;
    // }

    return LUT;
}

std::vector<std::complex<float>> PSK::generate_LUT(int num_of_symbols){//generates Look Up Table for M-PSK
    std::vector<std::complex<float>>LUT(num_of_symbols);
    for (int i = 0; i < num_of_symbols; i++){
            std::vector<double> I_and_Q(2);
            uint16_t gray_encoding = i ^ (i >> 1);
            double theta = 2 * M_PI * gray_encoding / num_of_symbols+ M_PI / num_of_symbols;
            std::complex<float> IQ_complex = static_cast<std::complex<float>>(std::polar(1.,theta));

            LUT[i] = IQ_complex;
        }
    return LUT;
}
        
//instantiate the modulators
QAM::QAM(int num_of_symbols){
    this->num_of_symbols = num_of_symbols;
    this->LUT = generate_LUT(num_of_symbols);
}
PSK::PSK(int num_of_symbols){
    this->num_of_symbols = num_of_symbols;
    this->LUT = generate_LUT(num_of_symbols);
}

//modulate a number based on the current modulation settings
std::complex<float> Modulator::modulate(uint16_t number_to_modulate){
    return LUT[number_to_modulate];
}

//prints the current look up table in order for debugging
void Modulator::print_LUT(){
    for (int i = 0; i < LUT.size(); i++){
        std::cout<<"index "<<i<<" in LUT is "<<LUT[i]<<std::endl;
    }
}


// int main(){
//     QAM QAM_16(16);
//     PSK PSK_16(4);

//     for (int i = 0; i < QAM_16.num_of_symbols; i++){
//         std::cout<<i<<" gets modulated to "<<QAM_16.modulate(i)<<std::endl;
//     }
//     std::cout<<"PSK:\n\n";
//     for (int i = 0; i < PSK_16.num_of_symbols; i++){
//         std::cout<<i<<" gets modulated to "<<PSK_16.modulate(i)<<std::endl;
//     }
// }
