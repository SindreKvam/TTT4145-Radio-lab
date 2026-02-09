#include <iostream>
#include <vector>
#include <cmath>
#include <complex>
#include <algorithm>


class Modulator{
    private:

        std::vector<std::vector<int>>LUT;

        std::vector<std::vector<int>>generate_LUT(int size){//generates Look Up Table for M-QAM
            std::vector<std::vector<int>>graycodes(size, std::vector<int>(2));
            //makes a 2d vector
            std::vector<std::vector<int>>graycode_grid(static_cast<int>(std::sqrt(size)),std::vector<int>(static_cast<int>(std::sqrt(size)))); 
            std::vector<int> horisontal_gray_codes(std::sqrt(size));
            std::vector<int> vertical_gray_codes(std::sqrt(size));

            //creates horisontal gray codes
            for (int i = 1; i < std::sqrt(size); i++){
                horisontal_gray_codes[i] = i ^ (i >> 1); 
            }

            vertical_gray_codes = horisontal_gray_codes;
            //shiftoperation to all elements in array to the left
            std::transform(vertical_gray_codes.begin(), vertical_gray_codes.end(), vertical_gray_codes.begin(),
            [size](int x){return x << static_cast<int>(std::log2(size)) / 2;});

            for (int i = 0; i < vertical_gray_codes.size(); i++){
                for (int j = 0; j < horisontal_gray_codes.size(); j++){
                    graycode_grid[i][j] = vertical_gray_codes[i] ^ horisontal_gray_codes[j];// just for visualization
                    graycodes[graycode_grid[i][j]] = {i, j};
                }
            }
            //only for visualisation
            // for (int i = 0; i < vertical_gray_codes.size(); i++){
            //     for (int j = 0; j < horisontal_gray_codes.size(); j++){
            //         std::cout<<graycode_grid[i][j]<<" ";
            //     }
            //     std::cout<<std::endl;
            // }

            return graycodes;
        }
        std::complex<double> PSK_modulation(uint16_t number_to_modulate){//do PSK modulation based on current settings give complex modulation
            std::vector<double> I_and_Q(2);
            uint16_t gray_encoding = number_to_modulate ^ (number_to_modulate >> 1);
            double theta = 2 * M_PI * gray_encoding / num_of_symbols+ M_PI / num_of_symbols;

            std::complex<double> IQ_complex = std::polar(1.,theta);
            return IQ_complex;
        }
        std::complex<double>QAM_modulation(uint16_t number_to_modulate){//do QAM modulation based on current settings give complex modulation
            std::complex<double> modulation;
            std::vector<int>place_in_graycode_grid = LUT[number_to_modulate];


            int shift = (std::sqrt(num_of_symbols)-1);
            place_in_graycode_grid[0] = place_in_graycode_grid[0]*2 - shift;//some sick mappping getting centre at 0 and peaks at sqrt(M)-1
            place_in_graycode_grid[1] = place_in_graycode_grid[1]*2 - shift;

            double normalized_real = place_in_graycode_grid[1]/(std::sqrt(num_of_symbols) - 1);
            double normalized_imag = -place_in_graycode_grid[0]/(std::sqrt(num_of_symbols) - 1);//minus just to correspond with sketch

            modulation.real(normalized_real);
            modulation.imag(normalized_imag);

            //std::cout<<modulation.real()<<" "<<modulation.imag()<<std::endl;

            return modulation;
        }

    public:
        int num_of_symbols;
        std::string mod_scheme;
        
        //instantiate the modulator
        Modulator(std::string mod_scheme = "QAM", int num_of_symbols = 16){
            this->mod_scheme = mod_scheme;
            this->num_of_symbols = num_of_symbols;
            LUT = generate_LUT(num_of_symbols);
        }

        //modulate a number based on the current modulation settings
        std::complex<double>modulate(uint16_t number_to_modulate){
            std::complex<double>modulation;
            if (mod_scheme == "QAM"){
                modulation = QAM_modulation(number_to_modulate);
            }
            else if(mod_scheme == "PSK"){
                modulation = PSK_modulation(number_to_modulate);
            }
            return modulation;
        }

        //prints the current look up table in order for debugging
        void print_LUT(){
            for (int i = 0; i < LUT.size(); i++){
                std::cout<<"index "<<i<<" in LUT is "<<LUT[i][0]<<" "<<LUT[i][1]<<std::endl;
            }
        }
};


// int main(){
//     Modulator QAM_16("QAM",64);

//     for (int i = 0; i < QAM_16.num_of_symbols; i++){
//         std::cout<<i<<" gets modulated to "<<QAM_16.modulate(i)<<std::endl;
//     }
// }
