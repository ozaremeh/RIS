# src/gui/widgets/system_monitor_graphs.py

import psutil
import pyqtgraph as pg
from collections import deque

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import QTimer, Qt


class SystemMonitorGraphs(QWidget):
    """Compact RAM + CPU + Unified Memory graphs for the Performance tab."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.max_points = 60
        self.ram_history = deque(maxlen=self.max_points)
        self.cpu_history = deque(maxlen=self.max_points)
        self.unified_history = deque(maxlen=self.max_points)

        self._build_ui()
        self._start_timer()

    # --------------------------------------------------------------- UI

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        title = QLabel("Performance Graphs", self)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(title)

        # ------------------ RAM Graph ------------------
        self.ram_plot = pg.PlotWidget()
        self._configure_small_plot(self.ram_plot, "RAM (GB)")
        self.ram_curve = self.ram_plot.plot(
            pen=pg.mkPen(color=(50, 150, 255), width=2)
        )
        layout.addWidget(self.ram_plot)

        # ------------------ CPU Graph ------------------
        self.cpu_plot = pg.PlotWidget()
        self._configure_small_plot(self.cpu_plot, "CPU (%)")
        self.cpu_curve = self.cpu_plot.plot(
            pen=pg.mkPen(color=(255, 120, 50), width=2)
        )
        layout.addWidget(self.cpu_plot)

        # ------------------ Unified Memory Graph ------------------
        self.unified_plot = pg.PlotWidget()
        self._configure_small_plot(self.unified_plot, "Unified Mem (%)")
        self.unified_curve = self.unified_plot.plot(
            pen=pg.mkPen(color=(120, 50, 255), width=2)
        )
        layout.addWidget(self.unified_plot)

    def _configure_small_plot(self, plot_widget, ylabel):
        plot_widget.setFixedHeight(120)
        plot_widget.setBackground("w")
        plot_widget.showGrid(x=False, y=True)
        plot_widget.setLabel("left", ylabel)
        plot_widget.setMouseEnabled(x=False, y=False)
        plot_widget.hideButtons()
        plot_widget.setMenuEnabled(False)

    # --------------------------------------------------------------- Timer

    def _start_timer(self):
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._update_graphs)
        self.timer.start()

    # --------------------------------------------------------------- Update Loop

    def _update_graphs(self):
        # RAM usage (GB)
        mem = psutil.virtual_memory()
        used_gb = mem.used / (1024**3)
        self.ram_history.append(used_gb)
        x_ram = list(range(len(self.ram_history)))[::-1]
        self.ram_curve.setData(x_ram, list(self.ram_history))

        # CPU usage (%)
        cpu = psutil.cpu_percent()
        self.cpu_history.append(cpu)
        x_cpu = list(range(len(self.cpu_history)))[::-1]
        self.cpu_curve.setData(x_cpu, list(self.cpu_history))

        # Unified Memory Pressure (%)
        unified_percent = mem.percent
        self.unified_history.append(unified_percent)
        x_uni = list(range(len(self.unified_history)))[::-1]
        self.unified_curve.setData(x_uni, list(self.unified_history))
