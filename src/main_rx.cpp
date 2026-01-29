
#include "config.h"
#include "gui/window.h"
#include "radio/radio_rx.h"
#include <QApplication>
#include <iostream>
#include <queue>
#include <thread>

int main(int argc, char **argv) {

    QApplication app(argc, argv);
    Rx rx = Rx();

    // Instantiate queues for storing data
    std::queue<std::array<int16_t, I_Q_CHANNEL_BUFFER_SIZE>> i_queue;
    std::queue<std::array<int16_t, I_Q_CHANNEL_BUFFER_SIZE>> q_queue;
    bool stop = false;

    // Start threads
    std::thread t_rx(&Rx::rx_loop, &rx, std::ref(i_queue), std::ref(q_queue),
                     std::ref(stop));

    // GUI
    MainWindow w(std::ref(i_queue), std::ref(q_queue));
    // w.resize(1000, 600);
    w.show();

    int rc = app.exec();

    // while (true) {
    //
    //     if (i_queue.size() >= 3) {
    //         break;
    //     }
    // }
    //
    // stop = true;
    //
    // std::cout << "Printing I and Q queues" << std::endl;
    // for (int j = 0; j < 3; ++j) {
    //     std::array<int16_t, RX_BUFFER_SIZE> i_front = i_queue.front();
    //     std::array<int16_t, RX_BUFFER_SIZE> q_front = q_queue.front();
    //
    //     for (int k = 0; k < RX_BUFFER_SIZE; ++k) {
    //         std::cout << i_front[k] << "  " << q_front[k] << " ";
    //     }
    //     std::cout << std::endl;
    //
    //     std::cout << i_queue.size() << std::endl;
    //     i_queue.pop();
    //     q_queue.pop();
    // }

    t_rx.join();

    std::cout << "Main loop exited. Quitting" << std::endl;

    return rc;
}
