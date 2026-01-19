#include <iostream>
#include <random>
#include <vector>
#include <ctime>
#include <cmath>

template <typename T>
void print_vector(const std::vector<T>& v){
    for (const auto& x : v){
        std::cout << x << " ";
    }
    std::cout << std::endl;
}

std::vector<uint16_t> generate_random_message(int16_t len_of_frame){// len_of_frame = 16 64, 256....
    std::vector<uint16_t> message(int(len_of_frame / 16));
    int16_t bits_for_errorcorrection = std::log2(len_of_frame) + 1;

    for(int i = 0; i < message.size(); i++){
        uint16_t message_segment = rand();
        message[i] = message_segment;
    }

    for (int i = 0; i < bits_for_errorcorrection / 16 + 1; i ++){//idiot proofing if giga message requiering more than 16 fault detection bits
        if (bits_for_errorcorrection > 16){
            message[message.size()-i] >> 16;
        }
        else{
            message[message.size()-i] >> bits_for_errorcorrection;
        }
    }
    message[0] = message[0]>>bits_for_errorcorrection;
    print_vector(message);
    return message;
}

void format_message(std::vector<uint16_t> msg ){
    std::vector<uint16_t> formatted_message(msg.size());
    uint16_t bitmask = 0b1000'0000'0000'0000; 
    for (int bit_index = 0; bit_index < msg.size() * 16; bit_index++){
        bitmask >> 1;
        if (bitmask / 16 >= 1){
            bitmask = 0b1000'0000'0000'0000;
        }
        if (bitmask & bitmask-1 != 0){//checks if its not a power of two
            
        }
        
    }
    std::vector<uint16_t> formatted_msg(msg.size());
    for (int i = formatted_msg.size()-1; i >= 0; i--){

    }
}

void fault_protect_frame(std::vector<uint16_t>message){ //message must be formatted
    return;
}

int main(){
    std::srand(std::time(0));
    for (int i = 0; i < 100; i++){
        generate_random_message(64);
    }
}