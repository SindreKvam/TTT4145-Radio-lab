
#include "window.h"
#include <cmath>
#include <iostream>

MainWindow::MainWindow(
    std::queue<std::array<int16_t, I_Q_CHANNEL_BUFFER_SIZE>> &i_queue,
    std::queue<std::array<int16_t, I_Q_CHANNEL_BUFFER_SIZE>> &q_queue)
    : i_queue(i_queue), q_queue(q_queue) {

    setWindowTitle("SDR Time plot (I/Q)");

    auto *central = new QWidget(this);
    auto *layout = new QVBoxLayout(central);

    // Create plot
    plot = new QCustomPlot(this);
    layout->addWidget(plot);
    setCentralWidget(central);

    iGraph = plot->addGraph();
    qGraph = plot->addGraph();
    iGraph->setPen(QPen(Qt::blue));
    qGraph->setPen(QPen(Qt::red));

    plot->xAxis->setLabel("Sample");
    plot->yAxis->setLabel("Amplitude");
    plot->yAxis->setRange(-1000, 1000);

    timer.setInterval(16);
    connect(&timer, &QTimer::timeout, this, &MainWindow::onTick);
    timer.start();
}

void MainWindow::onTick() {

    if (i_queue.empty() || q_queue.empty()) {
        return;
    }

    i_front = i_queue.front();
    q_front = q_queue.front();

    // TODO: this should not happen here, but in next stage
    i_queue.pop();
    q_queue.pop();

    updatePlot();
}

void MainWindow::updatePlot() {
    QVector<double> x(I_Q_CHANNEL_BUFFER_SIZE), i(I_Q_CHANNEL_BUFFER_SIZE),
        q(I_Q_CHANNEL_BUFFER_SIZE);

    for (int n = 0; n < I_Q_CHANNEL_BUFFER_SIZE; ++n) {
        x[n] = n;
        i[n] = (double)i_front[n];
        q[n] = (double)q_front[n];
        std::cout << i[n] << q[n] << std::endl;
    }

    iGraph->setData(x, i);
    qGraph->setData(x, q);
    plot->xAxis->setRange(0, (int)I_Q_CHANNEL_BUFFER_SIZE);
    plot->replot();
}
