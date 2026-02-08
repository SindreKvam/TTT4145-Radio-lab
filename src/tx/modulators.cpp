#include <iostream>
#include <random>
#include <vector>
#include <ctime>
#include <cmath>
#include "fault_protection.h"
#include <complex>
#include <fstream>

/*Making LUT for M-QAM refferencable by int*/
std::vector<std::vector<int>>create_LUT(){
    std::fstream csv("gray_codes/graycodes.csv", std::ios::in);

    std::vector<std::vector<std::string>>LUT_string(0, std::vector<std::string>(3));
    std::vector<std::vector<int>>LUT(0, std::vector<int>(3));

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

        LUT_string.push_back(row);
    }

    for (std::vector<std::string> symbol: LUT_string){
        std::vector<int> numeric_line(3);

        //std::cout<<symbol[0]<<' '<<symbol[1]<<' '<<symbol[2]<<std::endl;
        if (std::isdigit(symbol[0][0])){
            numeric_line = {std::stoi(symbol[0]), std::stoi(symbol[1]), std::stoi(symbol[2])};
            LUT.push_back(numeric_line);
        }
    }

    // for (std::vector<int> symbol: LUT){
    //     std::cout<<symbol[0]<<' '<<symbol[1]<<' '<<symbol[2]<<std::endl;
    // }
    return LUT;
}
    


/*this gives the modulation of Phase Shift keying with M symbols and return a vector with 
the corresponding real and complex element, both as real values*/
std::vector<double> MPSK(uint16_t symbol, uint16_t number_of_symbols){
    std::vector<double> I_and_Q(2);
    uint16_t gray_encoding = symbol ^ (symbol >> 1);
    double theta = 2 * M_PI * gray_encoding / number_of_symbols+ M_PI / number_of_symbols;

    I_and_Q[0] = cos(theta);   // I
    I_and_Q[1] = sin(theta);   // Q

    return I_and_Q;
}



/*this gives the modulation of Phase Shift keying with M symbols and return a complex number
 with the correct phase and amplitude */
std::complex<double> MPSK_complex(uint16_t symbol, uint16_t number_of_symbols){
    std::vector<double> I_and_Q(2);
    uint16_t gray_encoding = symbol ^ (symbol >> 1);
    double theta = 2 * M_PI * gray_encoding / number_of_symbols+ M_PI / number_of_symbols;

    std::complex<double> IQ_complex = std::polar(1.,theta);
    return IQ_complex;
}



/*M-QAM returning the symbol as complex*/
std::complex<double> M_QAM_complex(uint16_t symbol, uint16_t number_of_symbols = 16){
    std::complex<double> modulation;
    std::vector<int> looked_up(3);
    static std::vector<std::vector<int>>LUT = create_LUT();

    //using the LUT to find the correct constillation
    for (std::vector<int>constilation:LUT){//constilation = [symbol, x_pos, y_pos]
        if (constilation[0]==symbol){
            looked_up = constilation;
            break;
        }
    }

    int shift = (std::sqrt(number_of_symbols)-1);
    looked_up[1] = looked_up[1]*2 - shift;//some sick mappping getting centre at 0 and peaks at sqrt(M)-1
    looked_up[2] = looked_up[2]*2 - shift;

    double normalized_real = looked_up[2]/(std::sqrt(number_of_symbols) - 1);
    double normalized_imag = -looked_up[1]/(std::sqrt(number_of_symbols) - 1);//minus just to correspond with sketch

    modulation.real(normalized_real);
    modulation.imag(normalized_imag);

    //std::cout<<modulation.real()<<" "<<modulation.imag()<<std::endl;

    return modulation;
}



// int main(){
//     //std::cout<<MPSK_complex(0101, 16)<<std::endl;
//     //create_LUT();
//     //QPSK_complex(16);
//     std::cout<<M_QAM_complex(13)<<std::endl;
// }
