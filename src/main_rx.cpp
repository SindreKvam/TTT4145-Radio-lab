
#include "radio/radio_rx.h"
#include <iostream>

int main(int argc, char **argv) {

    Rx rx = Rx();

    for (int i = 0; i < 3; ++i) {
        rx.buffer_refill();
    }

    std::cout << "Main loop exited. Quitting" << std::endl;

    return 0;
}
