#include "window.h"
#include <cmath>
#include <iostream>

MainWindow::MainWindow(SPSCRingBuffer<RxSlab *, GUI_SLAB_COUNT> &free_q,
                       SPSCRingBuffer<RxSlab *, GUI_SLAB_COUNT> &filled_q)
    : free_q_(free_q), filled_q_(filled_q) {

    setWindowTitle("SDR Real-time Plot");
    setupUi();

    timer.setInterval(33); // ~30 Hz
    connect(&timer, &QTimer::timeout, this, &MainWindow::onTick);
    timer.start();
}

void MainWindow::setupUi() {
    auto *central = new QWidget(this);
    auto *layout = new QVBoxLayout(central);

    // Time domain plot
    timePlot = new QCustomPlot(this);
    timePlot->addGraph(); // I
    timePlot->graph(0)->setPen(QPen(Qt::blue));
    timePlot->graph(0)->setName("I");

    timePlot->addGraph(); // Q
    timePlot->graph(1)->setPen(QPen(Qt::red));
    timePlot->graph(1)->setName("Q");

    timePlot->xAxis->setLabel("Sample Index");
    timePlot->yAxis->setLabel("Amplitude");
    timePlot->yAxis->setRange(-2048, 2047); // Full 12-bit range
    layout->addWidget(timePlot);

    // Constellation plot
    constellationPlot = new QCustomPlot(this);
    constellationPlot->addGraph();
    constellationPlot->graph(0)->setLineStyle(QCPGraph::lsNone);
    constellationPlot->graph(0)->setScatterStyle(
        QCPScatterStyle(QCPScatterStyle::ssDisc, 2));
    constellationPlot->graph(0)->setPen(QPen(Qt::darkGreen));

    constellationPlot->xAxis->setLabel("I");
    constellationPlot->yAxis->setLabel("Q");
    constellationPlot->xAxis->setRange(-4096, 4095);
    constellationPlot->yAxis->setRange(-4096, 4095);
    layout->addWidget(constellationPlot);

    setCentralWidget(central);
    resize(1000, 800);
}

void MainWindow::onTick() {
    RxSlab *slab = nullptr;
    RxSlab *latest_slab = nullptr;

    // Drain the queue to get the latest frame
    while (filled_q_.pop(slab)) {
        if (latest_slab) {
            free_q_.push(latest_slab);
        }
        latest_slab = slab;
    }

    if (latest_slab) {
        updatePlots(latest_slab->data, latest_slab->len);
        free_q_.push(latest_slab);
    }
}

void MainWindow::updatePlots(const int16_t *data, size_t len) {
    size_t n_samples = len / 2;
    if (n_samples == 0)
        return;

    QVector<double> x(n_samples), i_vals(n_samples), q_vals(n_samples);

    for (size_t idx = 0; idx < n_samples; ++idx) {
        x[idx] = idx;
        i_vals[idx] = static_cast<double>(data[idx * 2]);
        q_vals[idx] = static_cast<double>(data[idx * 2 + 1]);
    }

    // Update Time Plot
    timePlot->graph(0)->setData(x, i_vals);
    timePlot->graph(1)->setData(x, q_vals);
    timePlot->xAxis->setRange(0, n_samples);
    timePlot->replot(QCustomPlot::rpQueued);

    // Update Constellation Plot
    constellationPlot->graph(0)->setData(i_vals, q_vals);
    constellationPlot->replot(QCustomPlot::rpQueued);
}
