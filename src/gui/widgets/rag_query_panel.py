# src/gui/widgets/rag_query_panel.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QLabel, QScrollArea
)
from PyQt6.QtCore import Qt

from orchestrator.orchestrator import send_message


class RAGQueryPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Ask RIS — Scientific Query")
        title.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)

        # Input box
        self.input_box = QTextEdit()
        self.input_box.setPlaceholderText(
            "Ask a scientific question grounded in your ingested papers...\n"
            "Examples:\n"
            "- What mechanisms of EphA2 activation appear across the literature?\n"
            "- Compare ligand-dependent and ligand-independent signaling.\n"
            "- What contradictions exist in EMT-related papers?"
        )
        layout.addWidget(self.input_box)

        # Run button
        run_layout = QHBoxLayout()
        self.run_button = QPushButton("Run Query")
        self.run_button.clicked.connect(self.run_query)
        run_layout.addWidget(self.run_button)
        layout.addLayout(run_layout)

        # Results area (scrollable)
        self.results_area = QTextEdit()
        self.results_area.setReadOnly(True)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.results_area)
        layout.addWidget(scroll)

    def run_query(self):
        question = self.input_box.toPlainText().strip()
        if not question:
            self.results_area.setPlainText("Please enter a question.")
            return

        # Call orchestrator (RAG route will trigger automatically)
        reply = send_message(question)

        # Display result
        self.results_area.setPlainText(reply)
