# src/gui/widgets/chat_panel.py

from datetime import datetime
import json

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QTabWidget, QComboBox, QScrollArea, QSizePolicy,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextCursor

from orchestrator.orchestrator import send_message_streaming, reset_history
from gui.widgets.message_block import MessageBlock
from gui.widgets.chat_stream_controller import ChatStreamController
from gui.widgets.system_monitor_stats import SystemMonitorStats
from gui.widgets.system_monitor_graphs import SystemMonitorGraphs


# ----------------------------------------------------------
# Model selector options (labels → override keys)
# ----------------------------------------------------------

MODEL_OPTIONS = {
    "Auto (Router decides)": None,
    "Phi-4 Reasoner": "reasoner",
    "Qwen2.5 72B (Writer)": "writer",
    "DeepSeek Coder": "coder",
    "DeepSeek Math 7B": "math",
}


class ChatInput(QTextEdit):
    """Multiline input with Enter-to-send, Shift+Enter for newline."""

    def __init__(self, parent, send_callback):
        super().__init__(parent)
        self._send_callback = send_callback

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.NoModifier:
            self._send_callback()
            return
        if event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
            return super().keyPressEvent(event)
        return super().keyPressEvent(event)


class ChatPanel(QWidget):
    """Modern, stable, bounce-free chat panel using QScrollArea."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.model_override = None  # updated by dropdown

        self._build_ui()
        self._connect_signals()

        # Streaming controller
        self.stream = ChatStreamController(
            self.message_layout,
            self._start_typing_indicator,
            self._stop_typing_indicator,
            scroll_area=self.scroll_area
        )

        # Initial system messages (UI only)
        self._append_system("Welcome to the Research Intelligence System.")
        self._append_system("Type a message below and press Enter or Send. Type /reset to clear history.")

    # ---------------------------------------------------------- UI

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        self.title_label = QLabel("Research Intelligence System", self)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        # Model selector
        self.model_selector = QComboBox(self)
        for label in MODEL_OPTIONS.keys():
            self.model_selector.addItem(label)
        layout.addWidget(self.model_selector)

        # Tabs
        self.tabs = QTabWidget(self)
        layout.addWidget(self.tabs, stretch=1)

        # Chat tab
        chat_tab = QWidget()
        chat_layout = QVBoxLayout(chat_tab)
        chat_layout.setContentsMargins(0, 0, 0, 0)

        # Scroll area
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.scroll_container = QWidget()
        self.message_layout = QVBoxLayout(self.scroll_container)
        self.message_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_area.setWidget(self.scroll_container)

        chat_layout.addWidget(self.scroll_area, stretch=1)

        # System monitor
        self.monitor_panel = SystemMonitorStats(self)
        chat_layout.addWidget(self.monitor_panel)

        self.tabs.addTab(chat_tab, "Chat")

        # Performance tab
        perf_tab = SystemMonitorGraphs(self)
        self.tabs.addTab(perf_tab, "Performance")

        # Router logs tab
        self.router_log = QTextEdit(self)
        self.router_log.setReadOnly(True)
        self.tabs.addTab(self.router_log, "Router Logs")

        # Input row
        input_row = QHBoxLayout()

        self.input_box = ChatInput(self, self._on_send_clicked)
        self.input_box.setPlaceholderText("Type your message...")
        self.input_box.setFixedHeight(110)
        self.input_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        input_row.addWidget(self.input_box, stretch=1)

        self.send_button = QPushButton("Send", self)
        input_row.addWidget(self.send_button)

        layout.addLayout(input_row)
        self.setLayout(layout)

    # ---------------------------------------------------------- Signals

    def _connect_signals(self) -> None:
        self.send_button.clicked.connect(self._on_send_clicked)
        self.model_selector.currentIndexChanged.connect(self._on_model_changed)

    def _on_model_changed(self):
        label = self.model_selector.currentText()
        self.model_override = MODEL_OPTIONS[label]
        self._append_system(f"Model override set to: {label}")

    # ---------------------------------------------------------- Message Helpers

    def _append_block(self, block: MessageBlock):
        self.message_layout.addWidget(block)
        self._scroll_to_bottom()
        return block

    def _append_system(self, text: str) -> None:
        block = MessageBlock(f"System: {text}", role="system")
        self._append_block(block)

    def _append_user(self, text: str) -> None:
        block = MessageBlock(f"You: {text}", role="user")
        self._append_block(block)

    # ---------------------------------------------------------- Typing Indicator

    def _start_typing_indicator(self):
        block = MessageBlock("Assistant: Reese is typing", role="assistant")
        self._typing_block = self._append_block(block)

    def _stop_typing_indicator(self):
        if hasattr(self, "_typing_block") and self._typing_block:
            self._typing_block.setParent(None)
            self._typing_block = None
            self._scroll_to_bottom()

    # ---------------------------------------------------------- Send / streaming

    def _on_send_clicked(self) -> None:
        user_text = self.input_box.toPlainText().strip()
        if not user_text:
            return

        self._append_user(user_text)
        self.input_box.clear()

        if user_text.lower() == "/reset":
            reset_history()
            self._append_system("Conversation history cleared.")
            return

        self._start_typing_indicator()

        first_token = True

        try:
            for token in send_message_streaming(
                user_text,
                override_model=self.model_override,
                router_callback=self._update_router_log,
            ):
                if first_token:
                    first_token = False
                    self._stop_typing_indicator()
                    self.stream.start_assistant_block()

                self.stream.append_token(token)

        except Exception as e:
            self._stop_typing_indicator()
            err_block = MessageBlock(f"Assistant: [Error] {e}", role="assistant")
            self._append_block(err_block)
            return

        if not first_token:
            self.stream.finalize()
        else:
            self._stop_typing_indicator()

    # ---------------------------------------------------------- Router log updater

    def _update_router_log(self, info: dict) -> None:
        try:
            pretty = json.dumps(info, indent=2)
        except Exception:
            pretty = str(info)

        self.router_log.append(pretty)
        self.router_log.moveCursor(QTextCursor.MoveOperation.End)

    # ---------------------------------------------------------- Scrolling

    def _scroll_to_bottom(self):
        self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        )
