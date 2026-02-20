#include <iostream>
#include <random>
#include <vector>
#include <ctime>
#include <cmath>
#include <algorithm>
#include <iomanip>

//for testing
#include <random>
#include <ctime>

#include "fault_protection.h"

void Hamming::test_encoding(){
    uint16_t parity = 0;

    //test of total parity
    for (int i = 0; i < window_size; i++){
        parity ^= tx_buffer[i];
    }

    std::cout<<"parity after total parity = "<<parity<<std::endl;
    if (!parity){
        std::cout<<"---parity check passed---"<<std::endl;
    }
    else{
        std::cout<<"---test failed---"<<std::endl;
    }

    for (auto it = index_of_parity_bits.begin() + 1; it != index_of_parity_bits.end(); it++){
        uint parity_index = *it;

        parity = 0;
        int gap = parity_index*2;
        
        for (int j = 0; j < window_size/parity_index/2; j++){
            for (int i = 0; i < parity_index; i++){
                parity ^= tx_buffer[parity_index + gap*j + i];
            }
        }
        if (!parity){
            std::cout<<"---passed parity index---"<<parity_index<<std::endl;
        }
        else{
            std::cout<<"---failed parity index---"<<parity_index<<std::endl;
        }
    }
    std::cout<<std::endl;
}

void print_binary(uint16_t num){
    uint16_t bitmask = 1<<15;
        while(bitmask){
            if (bitmask & num){std::cout<<1;}
            else{std::cout<<0;}
            bitmask >>= 1;
        }
}

//prints vectors
template<typename T>
std::ostream &operator<<(std::ostream &os, std::vector<T> &vec){
    std::cout<<"[";
    for (auto i:vec){
        std::cout<<i<<" ";
    }
    std::cout<<"]"<<std::endl;
    return os;
}

//Prints hamming window
std::ostream &operator<<(std::ostream &os, Hamming &hamming){
    //printing the buffer
    std::cout<<"tx_buffer =                     rx_buffer"<<std::endl;
    for (int i = 0; i < hamming.window_size; i++){
        print_binary(hamming.tx_buffer[i]);
        std::cout << " = " << std::hex << std::setw(4) << std::setfill('0') << hamming.tx_buffer[i] <<"     ";
        print_binary(hamming.rx_buffer[i]);
        std::cout << " = " << std::hex << std::setw(4) << std::setfill('0') << hamming.rx_buffer[i] << "   index = " << i;
        std::cout<<std::endl;

    }
    std::cout<<std::endl;

    //printing the parity bit index
    std::cout<<"parity bit indexes = ";
    for (auto i : hamming.index_of_parity_bits){
        std::cout<<i<<" ";
    }
    std::cout<<std::endl;
    return os;
}

Hamming::Hamming(int window_size){
    int parity_bits_amount = int(std::log2(window_size))+1;
    tx_buffer.resize(window_size,0);// makes the vector fill with zeros to the correct size
    rx_buffer.resize(window_size,0);

    this->index_of_parity_bits.reserve(parity_bits_amount);
    this->window_size = window_size;

    //get to know where to put the error correction bits
    index_of_parity_bits.push_back(0);
    int parity_bit_index = 1;
    while (parity_bit_index < window_size){
        index_of_parity_bits.push_back(parity_bit_index);
        parity_bit_index <<= 1;
    } 
}

void Hamming::put_into_buffer(uint16_t value){
    //are we on a bit index dedicated to parity bits? if so skip the index
    while(std::find(index_of_parity_bits.begin(), index_of_parity_bits.end(), index_tx_buffer) != index_of_parity_bits.end()){
        index_tx_buffer++;
    }
    tx_buffer[index_tx_buffer] = value;   
    
    index_tx_buffer++;
    //setting flag
    if (index_tx_buffer == window_size){
        ready_to_send_buffer = true;
    }
}

void Hamming::encode(){
    uint16_t bitmask = 1 << 15;
    std::vector<uint16_t> flipper(window_size, 0); // will be used to figure what bits to flip
    int h_index = 0; //horizontal index

    //find out what bits to flip
    while (bitmask){
        for (int v_index = 0; v_index < window_size; v_index++){
            if (bitmask & tx_buffer[v_index]){
                flipper[h_index] ^= v_index;    
            }
        }
        bitmask>>=1;
        h_index++;
    }

    uint16_t error_corr_h_pos = 1 << (int(std::log2(window_size))-1);

    //actually flip the bits
    for (uint16_t v_index : index_of_parity_bits){

        bitmask = 1<<15;
        h_index = 0;
        while (bitmask)
        {   
            if (flipper[h_index] & v_index){
                tx_buffer[v_index] |= bitmask;
            }
            bitmask >>= 1;
            h_index ++;
        }
        
    }

    //set total-parity bits
    for (int i = 1; i < window_size; i++){
        tx_buffer[0] ^= tx_buffer[i];
    }

}

void Hamming::decode(){
    uint16_t bitmask = 1 << 15;
    std::vector<uint16_t> flipper(window_size, 0); // will be used to figure what bits to flip
    int h_index = 0; //horizontal index

    uint16_t resend_v_line = 0;//i message is 

    //find out what bit to flip 
    while (bitmask){
        for (int v_index = 0; v_index < window_size; v_index++){
            if (bitmask & rx_buffer[v_index]){
                flipper[h_index] ^= v_index;    
            }
        }
        bitmask>>=1;
        h_index++;
    }

    std::cout<<"flipper = "<<flipper<<std::endl;


    //flips the correct bits
    bitmask = 1<<15;
    for (uint16_t flip_index:flipper){
        rx_buffer[flip_index] ^= (rx_buffer[flip_index] & bitmask);
        bitmask >>= 1;
    }

    //checks total parity
    uint16_t total_parity = 0;//one means that there is parity as the flipping flips do magic
    for (uint16_t message: rx_buffer){
        total_parity ^= message;
    }

    print_binary(total_parity);
    std::cout<<std::endl<<"= total parity";

    bitmask = 1 << 15;
    while (bitmask)
    {
        if(total_parity & bitmask){
            resend_v_line |= bitmask;
        }
        bitmask >>= 1;
    }

}

void Hamming::force_encode(){
    encode();
}

void Hamming::force_decode(){
    decode();
}

void Hamming::scramble_message(){
    std::srand(std::time(0));
    std::vector<uint16_t> error_index(16, 0);

    uint16_t bitmask = 1 << 15;
    uint16_t h_index = 0;
    while (bitmask){
        int random_indx = std::rand()%window_size;
        rx_buffer[random_indx]^=bitmask;
        bitmask >>= 1;
    }
    
}

void Hamming::internal_transfer(){
    rx_buffer = tx_buffer;
}

// int main(){
//     int size = 16;
//     int i = 0;
//     Hamming ham = Hamming(16);
//     // while (!ham.ready_to_send_buffer){
//     //     ham.put_into_buffer(i);
//     //     i++;
//     // }
//     ham.put_into_buffer(0x1234);
//     ham.put_into_buffer(0xABCD);
//     ham.put_into_buffer(0xDEAD);
//     ham.put_into_buffer(0xBABE);
//     ham.put_into_buffer(0xEF01);
//     ham.put_into_buffer(0x5678);
//     ham.put_into_buffer(0xFEDC);
//     ham.put_into_buffer(0x0120);
//     ham.put_into_buffer(0x1623);
//     ham.put_into_buffer(0x5678);
//     ham.put_into_buffer(0xAF04);

//     ham.force_encode();
//     std::cout<<ham<<std::endl;
//     ham.test_encoding();
    
//     //test scrambler
//     ham.internal_transfer();
//     ham.scramble_message();
//     std::cout<<ham<<std::endl;    

//     ham.force_decode();
//     std::cout<<ham<<std::endl;

    
//     //ham.print_internals();
// }
