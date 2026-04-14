#include "../../include/config.h"
#include "../core/root_raised_cosine.h"
#include "../modem/modem.h"
#include <vector>
#include <cstdint>
#include <complex>
#include <iostream>


class Symbol_sync{
    protected:
    //data storage
    std::complex<float> current_raw_value;
    std::complex<float> prev_raw_value;

    //decided data in polar coordinates but snapped to constillation
    std::complex<float> current_decided_value;
    std::complex<float> prev_decided_value;

    //output value actuall time synced IQ will be displaied for sps amount of samples
    std::complex<float> out;

    //sample information
    int sps;
    int n; //samples since last symbol

    //errors
    float timing_error;
    float timing_error_estimate;
    
    //used modulation scheme
    Modem modem;


    //private functions only used by public functions
    
    //interpolate using internal previously calculated error and freshly sampeled sample, stores result in out.
    void interpolate();
    void get_timing_error();

    public:
    //(de)constructor
    Symbol_sync(int sps, Modem modem); // samples pr symbol and current modulation sceme 
    ~Symbol_sync();

    //functions
    void sample_sig(std::complex<float> sample);

    //friends
    friend std::ostream &operator<<(std::ostream &os, Symbol_sync &symbol_sync);
};



