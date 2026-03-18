"""PyQtGraph-based live dashboard for visualizing TX/RX data - Simplified version."""

import logging
import multiprocessing as mp
import queue
import sys

import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QGridLayout, QLabel, QMainWindow, QWidget

from radiolab.config.config import Config

logger = logging.getLogger(__name__)

pg.setConfigOptions(antialias=True)


class LiveDashboard(QMainWindow):
    """Live dashboard for continuous TX/RX visualization.

    Simplified layout with 4 widgets:
    1. TX I/Q waveform
    2. RX I/Q waveform
    3. Transmitted image
    4. Received image
    """

    def __init__(self, config: Config, gui_queue: mp.Queue):
        super().__init__()
        self.config = config
        self.gui_queue = gui_queue

        # Data storage
        self.tx_const_symbols = None
        self.rx_const_symbols = None
        self.tx_payload = None
        self.rx_payload = None
        self.image_shape = None
        self.frame_count = 0
        self.frame_sync_locked = False
        self.last_sync_count = 0

        # Setup UI
        self.setWindowTitle("Radiolab - TX/RX Dashboard")
        self.resize(1600, 1000)

        # Create central widget with grid layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QGridLayout(central_widget)

        # Set stretch factors for equal sizing
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        layout.setRowStretch(0, 1)  # Waveforms row
        layout.setRowStretch(1, 1)  # Images row

        # Status label at top
        self.status_label = QLabel("Initializing...")
        self.status_label.setStyleSheet(
            "QLabel { background-color: #333; color: white; padding: 5px; font-size: 14px; }"
        )
        layout.addWidget(self.status_label, 0, 0, 1, 2)

        # Create plots
        self._create_plots(layout)

        # Setup update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_plots)
        self.timer.start(config.gui.update_rate_ms)

        logger.info("Dashboard initialized (simplified layout)")

    def _create_plots(self, layout):
        """Create the 4 main widgets: TX constellation, RX constellation, TX image, RX image."""

        # Row 1: TX and RX constellation diagrams
        self.tx_const_plot = pg.PlotWidget(title="TX Constellation")
        self.tx_const_plot.setAspectLocked(True)
        self.tx_const_scatter = pg.ScatterPlotItem(
            size=5, pen=None, brush=pg.mkBrush(255, 100, 100, 200)
        )
        self.tx_const_plot.addItem(self.tx_const_scatter)
        layout.addWidget(self.tx_const_plot, 1, 0)

        self.rx_const_plot = pg.PlotWidget(title="RX Constellation")
        self.rx_const_plot.setAspectLocked(True)
        self.rx_const_scatter = pg.ScatterPlotItem(
            size=5, pen=None, brush=pg.mkBrush(100, 255, 100, 200)
        )
        self.rx_const_plot.addItem(self.rx_const_scatter)
        layout.addWidget(self.rx_const_plot, 1, 1)

        # Row 2: TX and RX images
        self.tx_image = pg.ImageView()
        self.tx_image.ui.roiBtn.hide()
        self.tx_image.ui.menuBtn.hide()
        self.tx_image.setWindowTitle("Transmitted Image")
        layout.addWidget(self.tx_image, 2, 0)

        self.rx_image = pg.ImageView()
        self.rx_image.ui.roiBtn.hide()
        self.rx_image.ui.menuBtn.hide()
        self.rx_image.setWindowTitle("Received Image")
        layout.addWidget(self.rx_image, 2, 1)

    def _update_plots(self):
        """Update all plots with latest data."""
        # Drain queue
        updated = False
        while True:
            try:
                msg = self.gui_queue.get_nowait()
                self._process_message(msg)
                updated = True
            except queue.Empty:
                break

        if not updated:
            return

        # Determine sync status
        sync_text = "LOCKED" if self.frame_sync_locked else "SEARCHING"
        sync_color = "#00ff00" if self.frame_sync_locked else "#ffaa00"

        # Update status bar
        tx_syms = len(self.tx_const_symbols) if self.tx_const_symbols is not None else 0
        rx_syms = len(self.rx_const_symbols) if self.rx_const_symbols is not None else 0
        self.status_label.setText(
            f"Frame: {self.frame_count} | Sync: <span style='color: {sync_color};'>{sync_text}</span> | "
            f"TX: {tx_syms} symbols | RX: {rx_syms} symbols"
        )

        # Update TX constellation
        if self.tx_const_symbols is not None:
            self.tx_const_scatter.setData(
                x=self.tx_const_symbols.real[:500], y=self.tx_const_symbols.imag[:500]
            )

        # Update RX constellation
        if self.rx_const_symbols is not None:
            self.rx_const_scatter.setData(
                x=self.rx_const_symbols.real[:500], y=self.rx_const_symbols.imag[:500]
            )

        # Update TX image
        if self.tx_payload is not None and self.image_shape is not None:
            self._display_image(self.tx_payload, self.tx_image, "TX")

        # Update RX image
        if self.rx_payload is not None and self.image_shape is not None:
            self._display_image(self.rx_payload, self.rx_image, "RX")

    def _display_image(self, payload, image_widget, label):
        """Display image with proper scaling and rotation.

        Args:
            payload: 1D array of quantized pixel values
            image_widget: PyQtGraph ImageView widget
            label: "TX" or "RX" for logging
        """
        try:
            # Reshape to 2D image
            img = payload.reshape(self.image_shape)

            # FIX 1: Image rotation - Transpose if needed
            # OpenCV loads images as (height, width) but we might have dimensions swapped
            if img.shape[0] > img.shape[1]:
                # More rows than columns - good, keep as is
                pass
            else:
                # More columns than rows - transpose to rotate 90°
                img = img.T

            # FIX 2: Proper color scaling for M-QAM
            # For 4-QAM: values are 0, 1, 2, 3
            # We want 4 distinct grayscale levels
            m = self.config.phy.modulation_order
            if m == 4:
                # Map: 0→0, 1→85, 2→170, 3→255
                level_size = 255 // (m - 1)
                img_scaled = (img * level_size).astype(np.uint8)
            elif m == 16:
                # Map: 0→0, 1→17, 2→34, ..., 15→255
                level_size = 255 // (m - 1)
                img_scaled = (img * level_size).astype(np.uint8)
            else:
                # Generic scaling for other modulation orders
                img_scaled = np.clip((img / float(m - 1) * 255), 0, 255).astype(
                    np.uint8
                )

            # Display image
            image_widget.setImage(img_scaled, autoRange=False, autoLevels=False)

        except Exception as e:
            logger.debug(f"{label} image error: {e}")

    def _process_message(self, msg):
        """Process a message from the queue."""
        msg_type = msg.get("type")

        if msg_type == "tx_info":
            self.tx_payload = msg.get("payload")
            self.image_shape = msg.get("image_shape")
            logger.info(
                f"Dashboard received TX info - Shape: {self.image_shape}, "
                f"Modulation: {self.config.phy.modulation_order}-QAM"
            )

        elif msg_type == "tx_constellation":
            # TX constellation (modulated symbols before pulse shaping)
            self.tx_const_symbols = msg.get("symbols")

        elif msg_type == "rx_update":
            self.frame_count = msg.get("frame_count", 0)
            self.rx_const_symbols = msg.get("rx_constellation")
            self.rx_payload = msg.get("decoded_bits")

            # Track sync status
            if self.rx_payload is not None and len(self.rx_payload) > 0:
                if not self.frame_sync_locked:
                    logger.info("Frame sync: LOCKED")
                self.frame_sync_locked = True
                self.last_sync_count = self.frame_count
            else:
                # If no valid payload for 10 frames, mark as searching
                if self.frame_count - self.last_sync_count > 10:
                    self.frame_sync_locked = False


def gui_process(config: Config, gui_queue: mp.Queue, stop_event: mp.Event):
    """GUI process entry point.

    Args:
        config: System configuration
        gui_queue: Queue for receiving data
        stop_event: Event to signal shutdown
    """
    logger.info("GUI Process starting...")

    app = QApplication(sys.argv)
    window = LiveDashboard(config, gui_queue)
    window.show()

    # Check for shutdown periodically
    def check_shutdown():
        if stop_event.is_set():
            app.quit()

    shutdown_timer = QTimer()
    shutdown_timer.timeout.connect(check_shutdown)
    shutdown_timer.start(100)

    sys.exit(app.exec_())
