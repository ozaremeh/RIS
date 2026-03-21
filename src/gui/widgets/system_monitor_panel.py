# src/gui/widgets/system_monitor_panel.py

import psutil
import pyqtgraph as pg
from collections import deque

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGridLayout
from PyQt6.QtCore import QTimer, Qt


class SystemMonitorPanel(QWidget):
    """Compact system monitor with small RAM + CPU graphs."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Rolling buffers (60 seconds)
        self.max_points = 60
        self.ram_history = deque(maxlen=self.max_points)
        self.cpu_history = deque(maxlen=self.max_points)

        self._build_ui()
        self._start_timer()

    # --------------------------------------------------------------- UI

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        title = QLabel("System Monitor", self)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(title)

        # Numeric stats grid
        grid = QGridLayout()
        grid.setSpacing(2)

        self.total_label = QLabel("Total RAM: --", self)
        self.python_label = QLabel("Python RAM: --", self)
        self.lmstudio_label = QLabel("LM Studio RAM: --", self)

        grid.addWidget(self.total_label, 0, 0)
        grid.addWidget(self.python_label, 1, 0)
        grid.addWidget(self.lmstudio_label, 2, 0)

        layout.addLayout(grid)

        # ------------------ Compact RAM Graph ------------------
        self.ram_plot = pg.PlotWidget()
        self._configure_small_plot(self.ram_plot, "RAM (GB)")
        self.ram_curve = self.ram_plot.plot(
            pen=pg.mkPen(color=(50, 150, 255), width=2)
        )
        layout.addWidget(self.ram_plot)

        # ------------------ Compact CPU Graph ------------------
        self.cpu_plot = pg.PlotWidget()
        self._configure_small_plot(self.cpu_plot, "CPU (%)")
        self.cpu_curve = self.cpu_plot.plot(
            pen=pg.mkPen(color=(255, 120, 50), width=2)
        )
        layout.addWidget(self.cpu_plot)

    def _configure_small_plot(self, plot_widget, ylabel):
        """Configure a compact, minimalistic plot."""
        plot_widget.setFixedHeight(120)
        plot_widget.setBackground("w")
        plot_widget.showGrid(x=False, y=True)
        plot_widget.setLabel("left", ylabel)
        plot_widget.setLabel("bottom", "")
        plot_widget.setMouseEnabled(x=False, y=False)
        plot_widget.hideButtons()
        plot_widget.setMenuEnabled(False)

    # --------------------------------------------------------------- Timer

    def _start_timer(self):
        self.timer = QTimer(self)
        self.timer.setInterval(1000)  # 1 second
        self.timer.timeout.connect(self._update_stats)
        self.timer.start()

    # --------------------------------------------------------------- Helpers

    def _update_stats(self):
        # Total system RAM
        mem = psutil.virtual_memory()
        used_gb = mem.used / (1024**3)
        total_gb = mem.total / (1024**3)
        percent = mem.percent

        self.total_label.setText(
            f"Total RAM: {used_gb:.1f} / {total_gb:.1f} GB ({percent:.0f}%)"
        )

        # Python process RAM
        proc = psutil.Process()
        py_ram = proc.memory_info().rss / (1024**3)
        self.python_label.setText(f"Python RAM: {py_ram:.2f} GB")

        # LM Studio RAM
        lm_ram = self._find_lmstudio_ram()
        if lm_ram is None:
            self.lmstudio_label.setText("LM Studio RAM: (not running)")
        else:
            self.lmstudio_label.setText(f"LM Studio RAM: {lm_ram:.2f} GB")

        # ------------------ Update RAM graph ------------------
        self.ram_history.append(used_gb)
        x = list(range(len(self.ram_history)))[::-1]
        self.ram_curve.setData(x, list(self.ram_history))

        # ------------------ Update CPU graph ------------------
        cpu = psutil.cpu_percent()
        self.cpu_history.append(cpu)
        x2 = list(range(len(self.cpu_history)))[::-1]
        self.cpu_curve.setData(x2, list(self.cpu_history))

    def _find_lmstudio_ram(self):
        """Return LM Studio RAM usage in GB, or None if not found."""
        for p in psutil.process_iter(["name", "memory_info"]):
            name = p.info["name"]
            if not name:
                continue
            if "lmstudio" in name.lower():
                return p.info["memory_info"].rss / (1024**3)
        return None
