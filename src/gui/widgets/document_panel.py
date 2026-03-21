# src/gui/widgets/document_panel.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFileDialog, QTextEdit, QMessageBox
)
from PyQt6.QtCore import Qt

from document_tools import (
    load_docx,
    extract_full_document_context,
    apply_model_edits,
    save_docx
)

from orchestrator.orchestrator import send_message  # non-streaming call

import json
import os


class DocumentPanel(QWidget):
    """
    UI panel for loading, previewing, editing, and saving Word documents.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.current_doc = None
        self.current_path = None
        self.current_context = None

        self._build_ui()

    # ------------------------------------------------------------
    # UI
    # ------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Buttons row
        button_row = QHBoxLayout()

        self.open_button = QPushButton("Open Document…")
        self.open_button.clicked.connect(self._open_document)
        button_row.addWidget(self.open_button)

        self.send_button = QPushButton("Send to Writing Model")
        self.send_button.setEnabled(False)
        self.send_button.clicked.connect(self._send_to_model)
        button_row.addWidget(self.send_button)

        self.save_button = QPushButton("Save As…")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self._save_document)
        button_row.addWidget(self.save_button)

        layout.addLayout(button_row)

        # Preview area
        self.preview = QTextEdit(self)
        self.preview.setReadOnly(True)
        self.preview.setProperty("class", "transcript")
        layout.addWidget(self.preview, stretch=1)

        # Status label
        self.status_label = QLabel("No document loaded.")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    # ------------------------------------------------------------
    # Open document
    # ------------------------------------------------------------

    def _open_document(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Word Document",
            "",
            "Word Documents (*.docx)"
        )

        if not path:
            return

        try:
            self.current_doc = load_docx(path)
            self.current_path = path
            self.current_context = extract_full_document_context(path)

            self._update_preview()
            self.status_label.setText(f"Loaded: {os.path.basename(path)}")

            self.send_button.setEnabled(True)
            self.save_button.setEnabled(False)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load document:\n{e}")

    # ------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------

    def _update_preview(self):
        ctx = self.current_context
        if not ctx:
            self.preview.setText("No document loaded.")
            return

        text = []

        text.append("=== STRUCTURE ===\n")
        for item in ctx["structure"]["content"]:
            if item["type"] == "heading":
                text.append(f"[Heading] {item['level']}: {item['text']}")
            elif item["type"] == "paragraph":
                text.append(f"[Paragraph] {item['text']}")
            elif item["type"] == "table":
                text.append("[Table]")
                for row in item["rows"]:
                    text.append(" | ".join(row))
            text.append("")

        text.append("\n=== COMMENTS ===\n")
        for c in ctx["comments"]:
            text.append(f"- {c['text']}")

        text.append("\n=== TRACKED CHANGES ===\n")
        for ch in ctx["tracked_changes"]:
            text.append(f"[{ch['type']}] {ch['text']}")

        self.preview.setText("\n".join(text))

    # ------------------------------------------------------------
    # Send to writing model
    # ------------------------------------------------------------

    def _send_to_model(self):
        if not self.current_context:
            return

        # Prepare prompt
        prompt = (
            "You are a writing assistant. Here is the structure, comments, and tracked "
            "changes of a Word document. Produce a list of edits in JSON format.\n\n"
            f"{json.dumps(self.current_context, indent=2)}\n\n"
            "Return ONLY a JSON list of edits. Example:\n"
            '[{\"action\": \"replace\", \"target\": \"old\", \"new\": \"new\"}]'
        )

        try:
            # CRITICAL: bypass_memory=True
            response = send_message(
                prompt,
                override_model="qwen-72b-gguf",
                bypass_memory=True,
            )

            print("RAW MODEL RESPONSE:", repr(response))

            edits = json.loads(response)

            self.current_doc = apply_model_edits(self.current_doc, edits)
            self.status_label.setText("Edits applied.")
            self.save_button.setEnabled(True)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Model failed:\n{e}")

    # ------------------------------------------------------------
    # Save document
    # ------------------------------------------------------------

    def _save_document(self):
        if not self.current_doc:
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Revised Document",
            "",
            "Word Documents (*.docx)"
        )

        if not path:
            return

        try:
            save_docx(self.current_doc, path)
            self.status_label.setText(f"Saved to: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save document:\n{e}")


print("SEND_MESSAGE CALL:", send_message)
