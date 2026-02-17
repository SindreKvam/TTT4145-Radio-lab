#pragma once

#include <vector>
#include <cstdint>
#include <iostream>
#include <cmath>

class Hamming{
    private:
    uint16_t window_size; //will use log2(windowsize)+1 for fault detection
    std::vector<uint16_t> tx_buffer;//contains 16 window of bits including error correction
    std::vector<uint16_t> index_of_parity_bits;

    bool ready_to_send_buffer = 0;
    int index_window_buffer = 0;
    uint16_t window_buffer_bitmask; // used to track the possition on internal window buffer bits

    void encode();
    void decode();

    public:
    Hamming(uint16_t window_size);
    void put_into_buffer(uint16_t value);
    void print_internals();

    void force_encode();
    void force_decode();
};

