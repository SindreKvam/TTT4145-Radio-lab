import logging
import sys

# from queue import Empty, Queue
from multiprocessing import Event, Process
from multiprocessing.queues import Empty, Queue

import numpy as np

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
        self.rx_correlation = None
        self.rx_pll_error = None
        self.rx_pll_theta = None
        self.tx_image = None
        self.rx_image = None
        self.rx_metadata = None
        self.rx_debug = None
        self.rx_total_count = 0
        self.rx_decoded_count = 0
        self.rx_debug_sample_count = 0
        self.rx_fail_counts = {
            "coarse_no_peak": 0,
            "ted_too_short": 0,
            "fine_no_peak": 0,
            "header_decode_failed": 0,
            "agc_invalid_gain": 0,
            "exception": 0,
        }

        self.setWindowTitle("Radiolab - TX/RX Dashboard")
        self.resize(1600, 1000)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QGridLayout(central_widget)

        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 1)
        layout.setRowStretch(0, 0)
        layout.setRowStretch(1, 1)
        layout.setRowStretch(2, 1)
        layout.setRowStretch(3, 1)
        layout.setRowStretch(4, 1)

        self.status_label = QLabel("Initializing...")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label, 0, 0, 1, 3)

        self._create_plots(layout)

        self.timer = QTimer()
        self.timer.timeout.connect(self._update_plots)
        self.timer.start(config.gui.update_rate_ms)

    def _create_plots(self, layout: QGridLayout) -> None:
        """Instantiate plots that can be filled with data"""

        # Tx Constellation Plot
        self.tx_const_plot = pg.PlotWidget(title="TX Constellation")
        self.tx_const_plot.setAspectLocked(True)
        self.tx_const_scatter = pg.ScatterPlotItem(
            size=5, pen=None, brush=pg.mkBrush(255, 100, 100, 200)
        )
        self.tx_const_plot.addItem(self.tx_const_scatter)
        layout.addWidget(self.tx_const_plot, 1, 0)

        # Rx Constellation Plots
        self.rx_const_mf_plot = pg.PlotWidget(title="RX Matched filtered data")
        self.rx_const_mf_plot.setAspectLocked(True)
        self.rx_const_mf_scatter = pg.ScatterPlotItem(
            size=5, pen=None, brush=pg.mkBrush(100, 255, 100, 200)
        )
        self.rx_const_mf_plot.addItem(self.rx_const_mf_scatter)
        self.rx_const_mf_plot.setXRange(-1.2, 1.2, padding=0)
        self.rx_const_mf_plot.setYRange(-1.2, 1.2, padding=0)
        layout.addWidget(self.rx_const_mf_plot, 1, 1)

        self.rx_const_pll_plot = pg.PlotWidget(title="RX Phase locked data")
        self.rx_const_pll_plot.setAspectLocked(True)
        self.rx_const_pll_scatter = pg.ScatterPlotItem(
            size=5, pen=None, brush=pg.mkBrush(100, 255, 100, 200)
        )
        self.rx_const_pll_plot.addItem(self.rx_const_pll_scatter)
        self.rx_const_pll_plot.setXRange(-1.2, 1.2, padding=0)
        self.rx_const_pll_plot.setYRange(-1.2, 1.2, padding=0)
        layout.addWidget(self.rx_const_pll_plot, 1, 2)

        # Rx Correlation plot
        self.rx_correlation_plot = pg.PlotWidget(title="Rx Correlation data")
        # self.rx_correlation_plot.setAspectLocked(True)
        self.rx_correlation_curve = pg.PlotCurveItem(
            pen=pg.mkPen(color=(100, 200, 100), width=2)
        )
        self.rx_correlation_plot.addItem(self.rx_correlation_curve)
        layout.addWidget(self.rx_correlation_plot, 2, 0)

        self.tx_image_view = pg.ImageView()
        self.tx_image_view.ui.roiBtn.hide()
        self.tx_image_view.ui.menuBtn.hide()
        self.tx_image_view.setWindowTitle("Transmitted image")
        layout.addWidget(self.tx_image_view, 4, 0)

        self.rx_image_view = pg.ImageView()
        self.rx_image_view.ui.roiBtn.hide()
        self.rx_image_view.ui.menuBtn.hide()
        self.rx_image_view.setWindowTitle("Received image")
        layout.addWidget(self.rx_image_view, 4, 1)

        # PLL phase error plot
        self.rx_pll_error_plot = pg.PlotWidget(title="RX PLL Phase Error")
        self.rx_pll_error_curve = pg.PlotCurveItem(
            pen=pg.mkPen(color=(200, 120, 120), width=2)
        )
        self.rx_pll_error_plot.addItem(self.rx_pll_error_curve)
        layout.addWidget(self.rx_pll_error_plot, 2, 1)

        self.rx_pll_theta_plot = pg.PlotWidget(title="RX PLL Theta")
        self.rx_pll_theta_curve = pg.PlotCurveItem(
            pen=pg.mkPen(color=(120, 120, 220), width=2)
        )
        self.rx_pll_theta_plot.addItem(self.rx_pll_theta_curve)
        layout.addWidget(self.rx_pll_theta_plot, 2, 2)

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
                x=self.rx_symbols_mf.real,
                y=self.rx_symbols_mf.imag,
            )

        if self.rx_symbols_pll is not None:
            self.rx_const_pll_scatter.setData(
                x=self.rx_symbols_pll.real,
                y=self.rx_symbols_pll.imag,
            )

        # Update correlation plot
        if self.rx_correlation is not None:
            self.rx_correlation_curve.setData(
                x=np.arange(0, len(self.rx_correlation), 1),
                y=self.rx_correlation,
            )

        # Update PLL phase error plot
        if self.rx_pll_error is not None:
            self.rx_pll_error_curve.setData(
                x=np.arange(0, len(self.rx_pll_error), 1),
                y=self.rx_pll_error,
            )

        if self.rx_pll_theta is not None:
            self.rx_pll_theta_curve.setData(
                x=np.arange(0, len(self.rx_pll_theta), 1),
                y=self.rx_pll_theta,
            )

        # Update Tx constellation
        if self.tx_const_symbols is not None:
            self.tx_const_scatter.setData(
                x=self.tx_const_symbols.real,
                y=self.tx_const_symbols.imag,
            )

        if self.tx_image is not None:
            self.tx_image_view.setImage(self.tx_image)

        if self.rx_image is not None:
            self.rx_image_view.setImage(self.rx_image)

    def _process_message(self, msg):
        """Process message from the queue"""

        msg_type = msg.get("type")

        def _refresh_status(
            seq=None,
            reason="-",
        ):
            decode_rate = 0.0
            if self.rx_total_count > 0:
                decode_rate = 100.0 * self.rx_decoded_count / self.rx_total_count

            self.status_label.setText(
                f"RX seq={seq if seq is not None else '-'} | reason={reason} | "
                f"decoded={self.rx_decoded_count}/{self.rx_total_count} ({decode_rate:.1f}%) | "
                f"debug samples={self.rx_debug_sample_count} | "
                f"fails(sampled): coarse={self.rx_fail_counts['coarse_no_peak']} "
                f"ted={self.rx_fail_counts['ted_too_short']} "
                f"fine={self.rx_fail_counts['fine_no_peak']} "
                f"hdr={self.rx_fail_counts['header_decode_failed']} "
                f"agc={self.rx_fail_counts['agc_invalid_gain']} "
                f"exc={self.rx_fail_counts['exception']}"
            )

        match msg_type:
            case "rx_debug":
                self.rx_debug = msg
                self.rx_debug_sample_count += 1
                seq = msg.get("seq")
                if isinstance(seq, int):
                    self.rx_total_count = max(self.rx_total_count, seq + 1)

                reason = msg.get("reason", "unknown")
                if reason in self.rx_fail_counts:
                    self.rx_fail_counts[reason] += 1

                reason = msg.get("reason", "-")
                _refresh_status(
                    seq=msg.get("seq"),
                    reason=reason,
                )

            case "rx_debug_plot":
                plot = msg.get("plot")
                data = msg.get("data")
                if data is None or len(data) == 0:
                    return

                if plot == "correlation":
                    self.rx_correlation = data
                elif plot == "pll_error":
                    self.rx_pll_error = data
                elif plot == "pll_theta":
                    self.rx_pll_theta = data

            case "rx_update":
                # Keep rx_debug correlation as primary for diagnostics.
                self.rx_symbols_mf = msg.get("matched_filtered_preview")
                self.rx_symbols_pll = msg.get("phase_locked_preview")
                self.rx_metadata = msg.get("rx_metadata")
                rx_payload = msg.get("rx_payload")
                self.rx_decoded_count += 1

                if self.rx_metadata is not None:
                    expected_len = (
                        self.rx_metadata["img_width"]
                        * self.rx_metadata["img_height"]
                        * self.rx_metadata.get("channels", 3)
                    )
                    decoded_data = np.asarray(rx_payload[:expected_len], dtype=int)

                    self.rx_image = np.transpose(
                        np.reshape(
                            decoded_data,
                            (
                                self.rx_metadata["img_height"],
                                self.rx_metadata["img_width"],
                                self.rx_metadata.get("channels", 3),
                            ),
                        ),
                        (1, 0, 2),
                    )

                if self.rx_debug is not None:
                    _refresh_status(
                        seq=self.rx_debug.get("seq"),
                        reason="decoded_frame",
                    )
                else:
                    _refresh_status(reason="decoded_frame")

            case "tx_update":
                self.tx_const_symbols = msg.get("tx_const_preview")
                self.tx_image = msg.get("tx_image")
