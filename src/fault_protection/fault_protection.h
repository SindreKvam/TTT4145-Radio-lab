#pragma once

#include <algorithm>
#include <cmath>
#include <ctime>
#include <iostream>
#include <random>
#include <vector>

class Hamming {
  protected:
    int window_size; // will use log2(windowsize)+1 for fault detection
    std::vector<uint16_t>
        tx_buffer; // contains 16 window of bits including error correction
    std::vector<uint16_t> rx_buffer;

    std::vector<uint16_t> index_of_parity_bits;

    int index_tx_buffer = 0; // start inserting data on index 3 as the first 3
                             // are for faultprotection
    uint16_t window_buffer_bitmask; // used to track the possition on internal
                                    // window buffer bits

    void encode();
    void decode();

  public:
    bool ready_to_send_buffer = false;
    Hamming(int window_size);
    void put_into_buffer(uint16_t value);

    std::vector<uint16_t> encode_block(const std::vector<uint16_t> &data_words);
    std::vector<uint16_t>
    decode_block(const std::vector<uint16_t> &coded_words);

    void force_encode();
    void force_decode();

    // used for testing
    void scramble_message();
    void internal_transfer();
    void test_encoding();
    void test_decoding();

    friend std::ostream &operator<<(std::ostream &os, Hamming &hamming);
};
