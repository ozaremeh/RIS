# src/gui/widgets/model_status_panel.py

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import QTimer

from api_client import get_loaded_models


class ModelStatusPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.layout = QVBoxLayout(self)

        self.label = QLabel("Loaded models: (checking...)")
        self.refresh_button = QPushButton("Refresh")

        self.layout.addWidget(self.label)
        self.layout.addWidget(self.refresh_button)

        self.refresh_button.clicked.connect(self.update_status)

        # Optional: auto-refresh every 2 seconds
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_status)
        self.timer.start(2000)

        self.update_status()

    def update_status(self):
        try:
            models = get_loaded_models()
            if models:
                self.label.setText(
                    "Loaded models:\n" + "\n".join(f"• {m}" for m in models)
                )
            else:
                self.label.setText("Loaded models: none")
        except Exception as e:
            self.label.setText(f"Error checking models: {e}")
