# src/gui/widgets/memory_inspector_widget.py

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PyQt6.QtCore import QTimer
from gui.unified_memory_inspector import get_unified_memory_snapshot


class MemoryInspectorWidget(QWidget):
    def __init__(self, parent=None, poll_interval_ms=1500):
        super().__init__(parent)

        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(10, 10, 10, 10)

        self.title = QLabel("<b>Unified Memory Inspector</b>")
        self.layout().addWidget(self.title)

        self.system_label = QLabel()
        self.process_label = QLabel()
        self.suspicious_label = QLabel()

        for lbl in (self.system_label, self.process_label, self.suspicious_label):
            lbl.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Sunken)
            lbl.setLineWidth(1)
            self.layout().addWidget(lbl)

        # Polling timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_snapshot)
        self.timer.start(poll_interval_ms)

        self.update_snapshot()

    def update_snapshot(self):
        snap = get_unified_memory_snapshot()

        sys_mem = snap["system"]
        proc = snap["processes"]
        derived = snap["derived"]

        self.system_label.setText(
            f"<b>System Memory</b><br>"
            f"Total (est): {sys_mem['total_mb_est']:.1f} MB<br>"
            f"Free: {sys_mem['free_mb']:.1f} MB<br>"
            f"Active: {sys_mem['active_mb']:.1f} MB<br>"
            f"Inactive: {sys_mem['inactive_mb']:.1f} MB<br>"
            f"Wired: {sys_mem['wired_mb']:.1f} MB<br>"
            f"Compressed: {sys_mem['compressed_mb']:.1f} MB"
        )

        self.process_label.setText(
            f"<b>Processes</b><br>"
            f"LM Studio: {proc['lmstudio_mb']:.1f} MB<br>"
            f"llama.cpp: {proc['llamacpp_mb']:.1f} MB<br>"
            f"Python (orchestrator): {proc['python_mb']:.1f} MB"
        )

        suspicious = derived["suspicious_mb"]
        color = "red" if suspicious > 10_000 else "black"

        self.suspicious_label.setText(
            f"<b>Derived</b><br>"
            f"Used (est): {derived['used_mb_est']:.1f} MB<br>"
            f"<span style='color:{color}'>Suspicious: {suspicious:.1f} MB</span>"
        )
