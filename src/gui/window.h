#pragma once

#include "config.h"
#include "qcustomplot.h"
#include <QMainWindow>
#include <QTimer>
#include <QVBoxLayout>
#include <QWidget>
#include <array>
#include <cstdint>
#include <queue>

class MainWindow : public QMainWindow {
    Q_OBJECT
  public:
    MainWindow(
        std::queue<std::array<int16_t, I_Q_CHANNEL_BUFFER_SIZE>> &i_queue,
        std::queue<std::array<int16_t, I_Q_CHANNEL_BUFFER_SIZE>> &q_queue);

  private slots:
    void onTick();

  private:
    void updatePlot();

    QTimer timer;
    std::queue<std::array<int16_t, I_Q_CHANNEL_BUFFER_SIZE>> &i_queue;
    std::queue<std::array<int16_t, I_Q_CHANNEL_BUFFER_SIZE>> &q_queue;

    std::array<int16_t, I_Q_CHANNEL_BUFFER_SIZE> i_front{};
    std::array<int16_t, I_Q_CHANNEL_BUFFER_SIZE> q_front{};

    QCustomPlot *plot = nullptr;
    QCPGraph *iGraph = nullptr;
    QCPGraph *qGraph = nullptr;
};
