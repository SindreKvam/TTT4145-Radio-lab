#include "symbol_sync.h"
#include "../../include/config.h"
#include "../core/root_raised_cosine.h"
#include "../modem/modem.h"
#include <complex>
#include <cstdint>
#include <vector>
#include <iostream>

std::ostream &operator<<(std::ostream &os, Symbol_sync &symbol_sync) {
    os<<"--raw buffer--------decided buffer--:\n"<<std::endl;
    os<<"-----"<<symbol_sync.current_raw_value<<"----"<<symbol_sync.current_decided_value<<std::endl;
    return os;
}

Symbol_sync::Symbol_sync(int sps, Modem modem){
    //data storage info
    this->sps = sps;
    this->n = 0;
    this->modem = modem;
    
    //fill buffer
    this->current_raw_value = 0;
    this->prev_raw_value = 0;

    this->current_decided_value = 0;
    this->prev_decided_value = 0; 

    //fill errors
    this->timing_error = 0;
    this->timing_error_estimate = 0;
}

Symbol_sync::~Symbol_sync() = default;

void Symbol_sync::interpolate(){
    std::complex<float> delta_y = current_raw_value - prev_raw_value;
    out = current_raw_value + (delta_y * timing_error); 
}

void Symbol_sync::get_timing_error(){
    //multiplications naming scheme from drawing
    std::complex<float> upper_mult = prev_raw_value * std::conj(current_decided_value);
    std::complex<float> lower_mult = current_raw_value * std::conj(prev_decided_value);
    //the adder
    float error = std::real(lower_mult - upper_mult);
    float k_p = 0.01; // regulator parameter
    timing_error += error*k_p;

    //limit to 0 - 1 in range
    if (timing_error > 1){
        n++;
        timing_error -= 1;
    }
    else if (timing_error < 0){
        n--;
        timing_error += 1;
    }
}

void Symbol_sync::sample_sig(std::complex<float> sample){
    //updates the buffer values
    prev_raw_value = current_raw_value;
    current_raw_value = sample;

    prev_decided_value = current_decided_value;
    current_decided_value = modem.modulate(modem.demodulate(current_raw_value));
    
    //use previos stuff to figure what this sample should probably be via interpolation
    n++;
    if (n >= sps){
        n = 0; 
        interpolate();
        get_timing_error();
    } 
}


