"""GUI worker — live debug plots via PyQtGraph.

Runs in its own process.  Receives plot-data dicts from *plot_queue* via a
QTimer that fires at *config.gui_update_hz* (default 30 Hz).  The Qt event
loop is managed entirely inside this process.

Layout (3 × 2 grid):
  [0,0]  Constellation  pre-PLL  (payload symbols, I/Q scatter)
  [0,1]  Constellation  post-PLL (payload symbols, I/Q scatter)
  [1,0]  PLL error trace         (phase error in radians vs. symbol index)
  [1,1]  Decoded symbols         (stem / line plot of the last N symbols)
  [2,0]  TX image                (static — shown once at startup)
  [2,1]  RX image                (live — updated each DSP buffer)

Expected dict keys from dsp_worker:
  "pre_pll"   — complex ndarray, payload symbols before PLL
  "post_pll"  — complex ndarray, payload symbols after PLL
  "pll_error" — float ndarray, per-symbol PLL error (full buffer incl. preamble)
  "decoded"   — uint8 ndarray, demodulated symbol indices
  "rx_image"  — uint8 2-D ndarray (h × w), reconstructed image, or None

Expected one-shot key from main.py (sent once after workers start):
  "tx_image"  — uint8 2-D ndarray (h × w), the transmitted image

Design notes
------------
* PyQtGraph must be imported inside this process (after fork/spawn) so the
  Qt application object lives only here.
* PlotDataItems / ImageItems are created once; update() is called on them
  every tick to avoid recreating QGraphicsItems.
* If the queue is empty the timer fires but does nothing — no stale-data
  problem.
* The worker exits when the Qt window is closed (app.exec() returns).
"""

from __future__ import annotations

import multiprocessing as mp
import queue as _queue

import numpy as np
from config import RadioConfig
from utils.log import configure_logging, get_logger  # type: ignore[import]

# Maximum number of decoded symbols to display in the bottom-right panel
_MAX_DECODED_DISPLAY = 512


def gui_worker(config: RadioConfig, plot_queue: mp.Queue) -> None:  # type: ignore[type-arg]
    configure_logging(config.log_level, "gui")
    log = get_logger(__name__)

    # Fix Qt plugin path BEFORE any Qt library is imported.
    # cv2 ships its own incompatible libqxcb.so and its plugin dir ends up on
    # Qt's search path.  Importing PyQt5 at module level (in the main process)
    # would taint thread affinity state before the child starts, so we do it
    # here — inside the spawned process — just before pyqtgraph loads Qt.
    import os

    try:
        import PyQt5 as _pyqt5

        _plugin_root = os.path.join(os.path.dirname(_pyqt5.__file__), "Qt5", "plugins")
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.path.join(
            _plugin_root, "platforms"
        )
        os.environ["QT_PLUGIN_PATH"] = _plugin_root
    except ImportError:
        pass

    try:
        import pyqtgraph as pg  # type: ignore[import]
        from pyqtgraph.Qt import QtCore, QtWidgets  # type: ignore[import]
    except ImportError:
        log.error(
            "pyqtgraph is not installed.  GUI worker exiting.  "
            "Install with: pip install pyqtgraph pyqt5"
        )
        return

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    win = pg.GraphicsLayoutWidget(title="RadioLab — Live DSP Monitor", show=True)
    win.resize(1200, 900)

    # -----------------------------------------------------------------------
    # Row 0: constellations
    # -----------------------------------------------------------------------
    p_pre = win.addPlot(row=0, col=0, title="Constellation  pre-PLL")
    p_pre.setAspectLocked(True)
    p_pre.showGrid(x=True, y=True, alpha=0.3)
    scatter_pre = pg.ScatterPlotItem(
        size=3, pen=None, brush=pg.mkBrush(0, 180, 255, 120)
    )
    p_pre.addItem(scatter_pre)

    p_post = win.addPlot(row=0, col=1, title="Constellation  post-PLL")
    p_post.setAspectLocked(True)
    p_post.showGrid(x=True, y=True, alpha=0.3)
    scatter_post = pg.ScatterPlotItem(
        size=3, pen=None, brush=pg.mkBrush(0, 255, 100, 140)
    )
    p_post.addItem(scatter_post)

    # -----------------------------------------------------------------------
    # Row 1: PLL error + decoded symbols
    # -----------------------------------------------------------------------
    p_err = win.addPlot(row=1, col=0, title="PLL error (rad)")
    p_err.showGrid(x=True, y=True, alpha=0.3)
    p_err.setLabel("bottom", "Symbol index")
    p_err.setLabel("left", "Error (rad)")
    curve_err = p_err.plot(pen=pg.mkPen("y", width=1))
    vline_preamble = pg.InfiniteLine(
        pos=config.pll_preamble_length,
        angle=90,
        pen=pg.mkPen("r", width=1, style=QtCore.Qt.PenStyle.DashLine),
        label="end of preamble",
        labelOpts={"color": "r", "position": 0.9},
    )
    p_err.addItem(vline_preamble)

    p_dec = win.addPlot(
        row=1, col=1, title=f"Decoded symbols (last {_MAX_DECODED_DISPLAY})"
    )
    p_dec.showGrid(x=True, y=True, alpha=0.3)
    p_dec.setLabel("bottom", "Symbol index")
    p_dec.setLabel("left", "Symbol value")
    curve_dec = p_dec.plot(
        pen=None, symbol="o", symbolSize=3, symbolBrush=pg.mkBrush(255, 165, 0, 160)
    )

    # -----------------------------------------------------------------------
    # Row 2: TX image (static) + RX image (live)
    # -----------------------------------------------------------------------
    p_tx_img = win.addPlot(row=2, col=0, title="TX image")
    p_tx_img.setAspectLocked(True)
    p_tx_img.hideAxis("bottom")
    p_tx_img.hideAxis("left")
    img_tx = pg.ImageItem()
    p_tx_img.addItem(img_tx)

    p_rx_img = win.addPlot(row=2, col=1, title="RX image")
    p_rx_img.setAspectLocked(True)
    p_rx_img.hideAxis("bottom")
    p_rx_img.hideAxis("left")
    img_rx = pg.ImageItem()
    p_rx_img.addItem(img_rx)

    tx_image_set = False  # guard: only set the TX image once
    rx_image_ranged = False  # guard: autoRange on first RX image only

    # -----------------------------------------------------------------------
    # QTimer callback — drain plot_queue and update plots
    # -----------------------------------------------------------------------
    def _update() -> None:
        nonlocal tx_image_set, rx_image_ranged
        dsp_data = None
        # Drain queue: collect all items; keep the last DSP packet, but process
        # any tx_image message regardless of position in the queue.
        while True:
            try:
                item = plot_queue.get_nowait()
            except _queue.Empty:
                break
            if "tx_image" in item and not tx_image_set:
                tx_img_arr: np.ndarray = item["tx_image"]
                # pg.ImageItem expects (width, height); transpose + flipud for
                # upright display (image row 0 at the top).
                img_tx.setImage(np.flipud(tx_img_arr).T, levels=(0, 255))
                p_tx_img.autoRange()
                tx_image_set = True
            else:
                dsp_data = item  # keep latest DSP packet

        if dsp_data is None:
            return  # nothing new from DSP

        pre: np.ndarray = dsp_data.get("pre_pll", np.array([], dtype=complex))
        post: np.ndarray = dsp_data.get("post_pll", np.array([], dtype=complex))
        err: np.ndarray = dsp_data.get("pll_error", np.array([], dtype=float))
        dec: np.ndarray = dsp_data.get("decoded", np.array([], dtype=np.uint8))
        rx_img_arr = dsp_data.get("rx_image", None)

        if pre.size > 0:
            scatter_pre.setData(x=pre.real.astype(float), y=pre.imag.astype(float))
        if post.size > 0:
            scatter_post.setData(x=post.real.astype(float), y=post.imag.astype(float))
        if err.size > 0:
            curve_err.setData(y=err.astype(float))
            vline_preamble.setValue(min(config.pll_preamble_length, err.size - 1))
        if dec.size > 0:
            tail = dec[-_MAX_DECODED_DISPLAY:]
            curve_dec.setData(y=tail.astype(float))
        if rx_img_arr is not None and rx_img_arr.size > 0:
            img_rx.setImage(np.flipud(rx_img_arr).T, levels=(0, 255))
            if not rx_image_ranged:
                p_rx_img.autoRange()
                rx_image_ranged = True

    timer = QtCore.QTimer()
    timer.setInterval(max(1, int(1000 / config.gui_update_hz)))
    timer.timeout.connect(_update)
    timer.start()

    log.info("GUI running at %d Hz — close the window to exit.", config.gui_update_hz)
    app.exec()
    log.info("GUI worker exiting.")
