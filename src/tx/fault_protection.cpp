#include <iostream>
#include <random>
#include <vector>
#include <ctime>
#include <cmath>

void print_vector(std::vector<uint16_t> vector_to_be_printed){
    for (int i = 0; i < vector_to_be_printed.size(); i++){
        printf("%X", vector_to_be_printed[i]);
        //std::cout<<vector_to_be_printed[i]<<std::endl;
    }
    printf("\n");
}

std::vector<uint16_t> generate_random_message(int16_t len_of_frame){// len_of_frame = 16 64, 256....
    std::vector<uint16_t> message(int(len_of_frame / 16));
    std::srand(std::time(0));
    int16_t bits_for_errorcorrection = std::log2(len_of_frame) + 1;

    for(int i = 0; i < message.size(); i++){
        uint16_t message_segment = rand();
        message[i] = message_segment;
    }

    message[0] = message[0]>>bits_for_errorcorrection;
    print_vector(message);
    return message;
}

void format_message(std::vector<uint16_t> msg ){
    std::vector<uint16_t> powers_of_two;
    for (int bit_index = 0; bit_index < msg.size() * 16; bit_index++){
        
    }
    std::vector<uint16_t> formatted_msg(msg.size());
    for (int i = formatted_msg.size()-1; i >= 0; i--){

    }
}

void fault_protect_frame(std::vector<uint16_t>message){ //message must be formatted
    return 0;
}

int main(){
    generate_random_message(16);
}