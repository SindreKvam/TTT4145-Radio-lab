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
    MainWindow(SPSCRingBuffer<RxSlab *, GUI_SLAB_COUNT> &free_q,
               SPSCRingBuffer<RxSlab *, GUI_SLAB_COUNT> &filled_q);

  private slots:
    void onTick();

  private:
    void setupUi();
    void updatePlots(const int16_t *data, size_t len);

    SPSCRingBuffer<RxSlab *, GUI_SLAB_COUNT> &free_q_;
    SPSCRingBuffer<RxSlab *, GUI_SLAB_COUNT> &filled_q_;
    QTimer timer;

    QCustomPlot *timePlot = nullptr;
    QCustomPlot *constellationPlot = nullptr;
};
