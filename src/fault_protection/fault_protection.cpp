#include <iostream>
#include <random>
#include <vector>
#include <ctime>
#include <cmath>
#include <algorithm>

#include "fault_protection.h"

void Hamming::print_internals(){
    //printing the buffer
    int index = 0;
    std::cout<<"buffer = "<<std::endl;
    for (auto i : this->tx_buffer){
        uint16_t bitmask = 1<<15;
        while(bitmask){
            if (bitmask & i){std::cout<<1;}
            else{std::cout<<0;}
            bitmask >>= 1;
        }
        std::cout << " = " << i << " index = " << index;
        std::cout<<std::endl;
        index++;
    }
    std::cout<<std::endl;

    //printing the parity bit index
    std::cout<<"parity bit indexes = ";
    for (auto i : index_of_parity_bits){
        std::cout<<i<<" ";
    }
    std::cout<<std::endl;
}

Hamming::Hamming(int window_size){
    int parity_bits_amount = int(std::log2(window_size))+1;
    tx_buffer.resize(window_size,0);// makes the vector fill with zeros to the correct size

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
    //are we on a bit index dedicated to parity bits?
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

// this sucks.... not functional !!!!
void Hamming::encode(){
    uint16_t bitmask = 1;
    std::vector<uint16_t> flipper(window_size, 0); // will be used to figure what bits to flip
    
    int h_index = 0; //horizontal index
    while (bitmask){
        for (int i = 0; i < window_size; i++){
            if (bitmask & tx_buffer[i]){
                flipper[h_index] ^= i;    
            }
        }
        bitmask>>=1;
        h_index++;
    }

    bitmask = 1 << (int(std::log2(window_size))-1);
    while (bitmask){
        for (int i = 0; i < window_size; i++){
            if(bitmask & flipper[i]){
                tx_buffer[bitmask] |= bitmask;
            }
        }
        bitmask >>= 1;
    }
}

void Hamming::force_encode(){
    encode();
}

void Hamming::decode(){

}

// int main(){
//     int size = 16;
//     int i = 0;
//     Hamming ham = Hamming(16);
//     // while (!ham.ready_to_send_buffer){
//     //     ham.put_into_buffer(i);
//     //     i++;
//     // }
//     ham.put_into_buffer(1);
//     ham.put_into_buffer(0);
//     ham.put_into_buffer(1);
//     ham.put_into_buffer(0);
//     ham.put_into_buffer(1);
//     ham.put_into_buffer(0);
//     ham.put_into_buffer(1);
//     ham.put_into_buffer(0);
//     ham.put_into_buffer(1);
//     ham.put_into_buffer(0);
//     ham.put_into_buffer(1);

//     ham.force_encode();
    
    
//     ham.print_internals();
// }
