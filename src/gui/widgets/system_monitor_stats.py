# src/gui/widgets/system_monitor_stats.py

import psutil
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGridLayout
from PyQt6.QtCore import QTimer, Qt


class SystemMonitorStats(QWidget):
    """Displays numeric RAM usage stats (no graphs)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._start_timer()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        title = QLabel("System Monitor", self)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(2)

        self.total_label = QLabel("Total RAM: --", self)
        self.python_label = QLabel("Python RAM: --", self)
        self.lmstudio_label = QLabel("LM Studio RAM: --", self)

        grid.addWidget(self.total_label, 0, 0)
        grid.addWidget(self.python_label, 1, 0)
        grid.addWidget(self.lmstudio_label, 2, 0)

        layout.addLayout(grid)

    def _start_timer(self):
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._update_stats)
        self.timer.start()

    def _update_stats(self):
        mem = psutil.virtual_memory()
        used_gb = mem.used / (1024**3)
        total_gb = mem.total / (1024**3)
        percent = mem.percent

        self.total_label.setText(
            f"Total RAM: {used_gb:.1f} / {total_gb:.1f} GB ({percent:.0f}%)"
        )

        proc = psutil.Process()
        py_ram = proc.memory_info().rss / (1024**3)
        self.python_label.setText(f"Python RAM: {py_ram:.2f} GB")

        lm_ram = self._find_lmstudio_ram()
        if lm_ram is None:
            self.lmstudio_label.setText("LM Studio RAM: (not running)")
        else:
            self.lmstudio_label.setText(f"LM Studio RAM: {lm_ram:.2f} GB")

    def _find_lmstudio_ram(self):
        for p in psutil.process_iter(["name", "memory_info"]):
            name = p.info["name"]
            if name and "lmstudio" in name.lower():
                return p.info["memory_info"].rss / (1024**3)
        return None
