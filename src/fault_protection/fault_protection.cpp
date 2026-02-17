#include <iostream>
#include <random>
#include <vector>
#include <ctime>
#include <cmath>

#include "fault_protection.h"

void Hamming::print_internals(){
    //printing the buffer
    std::cout<<"buffer = ";
    for (auto i : this->buffer){
        std::cout<<i<<" ";
    }
    std::cout<<std::endl;

    //printing the parity bit index
    std::cout<<"parity bit indexes = ";
    for (auto i : index_of_parity_bits){
        std::cout<<i<<" ";
    }
    std::cout<<std::endl;
}

Hamming::Hamming(uint16_t window_size){
    int parity_bits_amount = int(std::log2(window_size))+1;
    this->tx_buffer.reserve(window_size);
    this->index_of_parity_bits.reserve(parity_bits_amount);

    //get to know where to put the error correction bits
    index_of_parity_bits.push_back(0);
    int parity_bit_index = 1;
    while (parity_bit_index < window_size){
        index_of_parity_bits.push_back(parity_bit_index);
        parity_bit_index <<= 1;
    } 
}

void Hamming::put_into_buffer(uint16_t value){
    uint16_t bitmask = 0b1000000000000000;
    while (bitmask > 0){

    }
}

// int main(){
//     Hamming ham = Hamming(16);
//     ham.print_internals();
// }
