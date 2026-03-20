import logging
import sys

# from queue import Empty, Queue
from multiprocessing import Event, Process
from multiprocessing.queues import Empty, Queue

# from threading import Event, Thread
import pyqtgraph as pg
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QGridLayout, QLabel, QMainWindow, QWidget

from radiolab.config.config import Config

logger = logging.getLogger(__name__)
pg.setConfigOptions(antialias=True)


class GuiWorker(Process):
    def __init__(
        self,
        gui_queue: Queue,
        config: Config,
        stop_event: Event,
        name: str = "GuiWorker",
    ) -> None:
        """"""
        super().__init__(name=name, daemon=True)
        self.gui_queue = gui_queue
        self.config = config
        self.stop_event = stop_event

    def run(self) -> None:
        app = QApplication(sys.argv)
        window = LiveDashboard(self.config, self.gui_queue)
        window.show()

        def check_shutdown():
            if self.stop_event.is_set():
                app.quit()

        shutdown_timer = QTimer()
        shutdown_timer.timeout.connect(check_shutdown)
        shutdown_timer.start(100)

        sys.exit(app.exec_())


class LiveDashboard(QMainWindow):
    """"""

    def __init__(self, config: Config, gui_queue: Queue):
        super().__init__()
        self.config = config
        self.gui_queue = gui_queue

        self.tx_const_symbols = None
        self.rx_symbols_mf = None
        self.rx_symbols_pll = None

        self.setWindowTitle("Radiolab - TX/RX Dashboard")
        self.resize(1600, 1000)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QGridLayout(central_widget)

        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 1)
        layout.setRowStretch(0, 1)
        layout.setRowStretch(1, 1)
        layout.setRowStretch(2, 1)

        self.status_label = QLabel("Initializing...")

        layout.addWidget(self.status_label, 0, 0, 1, 2)

        self._create_plots(layout)

        self.timer = QTimer()
        self.timer.timeout.connect(self._update_plots)
        self.timer.start(config.gui.update_rate_ms)

    def _create_plots(self, layout: QGridLayout) -> None:
        self.tx_const_plot = pg.PlotWidget(title="TX Constellation")
        self.tx_const_plot.setAspectLocked(True)
        self.tx_const_scatter = pg.ScatterPlotItem(
            size=5, pen=None, brush=pg.mkBrush(255, 100, 100, 200)
        )
        self.tx_const_plot.addItem(self.tx_const_scatter)
        layout.addWidget(self.tx_const_plot, 0, 0)

        self.rx_const_mf_plot = pg.PlotWidget(title="RX Matched filtered data")
        self.rx_const_mf_plot.setAspectLocked(True)
        self.rx_const_mf_scatter = pg.ScatterPlotItem(
            size=5, pen=None, brush=pg.mkBrush(100, 255, 100, 200)
        )
        self.rx_const_mf_plot.addItem(self.rx_const_mf_scatter)
        layout.addWidget(self.rx_const_mf_plot, 0, 1)

        self.rx_const_pll_plot = pg.PlotWidget(title="RX Phase locked data")
        self.rx_const_pll_plot.setAspectLocked(True)
        self.rx_const_pll_scatter = pg.ScatterPlotItem(
            size=5, pen=None, brush=pg.mkBrush(100, 255, 100, 200)
        )
        self.rx_const_pll_plot.addItem(self.rx_const_pll_scatter)
        layout.addWidget(self.rx_const_pll_plot, 0, 2)

    def _update_plots(self) -> None:
        """"""

        updated = False
        while True:
            try:
                msg = self.gui_queue.get_nowait()
                self._process_message(msg)
                updated = True
            except Empty:
                break

        if not updated:
            return

        # Update Rx constellations
        if self.rx_symbols_mf is not None:
            self.rx_const_mf_scatter.setData(
                x=self.rx_symbols_mf.real[:500],
                y=self.rx_symbols_mf.imag[:500],
            )

        if self.rx_symbols_pll is not None:
            self.rx_const_pll_scatter.setData(
                x=self.rx_symbols_pll.real[:500],
                y=self.rx_symbols_pll.imag[:500],
            )

        # Update Tx constellation
        if self.tx_const_symbols is not None:
            self.tx_const_scatter.setData(
                x=self.tx_const_symbols.real[:500],
                y=self.tx_const_symbols.imag[:500],
            )

    def _process_message(self, msg):
        """Process message from the queue"""

        msg_type = msg.get("type")

        match msg_type:
            case "rx_update":
                self.rx_symbols_mf = msg.get("matched_filtered_data")
                self.rx_symbols_pll = msg.get("phase_locked_data")

            case "tx_update":
                self.tx_const_symbols = msg.get("tx_data")
