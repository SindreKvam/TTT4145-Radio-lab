#pragma once

#include "config.h"
#include "core/spsc_ring.h"
#include "qcustomplot.h"
#include <QMainWindow>
#include <QTimer>
#include <QVBoxLayout>
#include <QWidget>
#include <array>
#include <cstdint>
#include <memory>

class MainWindow : public QMainWindow {
    Q_OBJECT
  public:
    MainWindow(RxRingBuffer &free_q, RxRingBuffer &filled_q);

  private slots:
    void onTick();

  private:
    void setupUi();
    void updatePlots(const int16_t *data, size_t len);

    RxRingBuffer &free_q_;
    RxRingBuffer &filled_q_;
    QTimer timer;

    QCustomPlot *timePlot = nullptr;
    QCustomPlot *constellationPlot = nullptr;
};
