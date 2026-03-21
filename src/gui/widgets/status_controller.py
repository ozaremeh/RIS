# src/gui/widgets/status_controller.py

from PyQt6.QtCore import QTimer
from llama_server_manager import get_llama_server_status


class StatusController:
    """Handles server status polling and updating the label."""

    def __init__(self, label):
        self.label = label

        self.timer = QTimer()
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self._refresh)
        self.timer.start()

        self._refresh()

    def _refresh(self):
        status = get_llama_server_status()
        if status == "running":
            text = "🟢 Writing Model Server: Running"
        else:
            text = "🔴 Writing Model Server: Offline"
        self.label.setText(text)
