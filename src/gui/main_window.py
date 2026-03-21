# src/gui/main_window.py

from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QLabel,
    QTextEdit, QGroupBox
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QTimer

from gui.widgets.chat_panel import ChatPanel
from gui.widgets.document_panel import DocumentPanel
from gui.widgets.system_monitor_graphs import SystemMonitorGraphs
from gui.widgets.model_status_panel import ModelStatusPanel
from gui.widgets.memory_inspector_widget import MemoryInspectorWidget
from gui.widgets.rag_query_panel import RAGQueryPanel

from orchestrator.orchestrator import send_message
from gui.unified_memory_inspector import get_unified_memory_snapshot

import json


class MainWindow(QMainWindow):
    """Main window for the Research Intelligence System GUI."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Research Intelligence System")
        self.setMinimumSize(900, 600)

        # Create tab widget
        self.tabs = QTabWidget(self)
        self.setCentralWidget(self.tabs)

        # Chat tab
        self.chat_panel = ChatPanel(self)
        self.tabs.addTab(self.chat_panel, "Chat")

        # Document tab
        self.document_panel = DocumentPanel(self)
        self.tabs.addTab(self.document_panel, "Documents")

        # Performance tab
        self.performance_panel = SystemMonitorGraphs(self)
        self.tabs.addTab(self.performance_panel, "Performance")

        # System tab (model status)
        system_tab = QWidget()
        system_layout = QVBoxLayout(system_tab)
        self.model_status_panel = ModelStatusPanel(self)
        system_layout.addWidget(self.model_status_panel)
        self.tabs.addTab(system_tab, "System")

        # Unified Memory Inspector tab
        self.memory_inspector = MemoryInspectorWidget(self)
        self.tabs.addTab(self.memory_inspector, "Unified Memory")

        # Router Debug Tab
        self.router_debug_panel = self._create_router_debug_panel()
        self.tabs.addTab(self.router_debug_panel, "Router Debug")

        # Scientific Query (RAG) tab
        self.rag_query_panel = RAGQueryPanel(self)
        self.tabs.addTab(self.rag_query_panel, "Scientific Query")

        # Status Bar: Memory Summary
        self.memory_status = QLabel("Memory: -- MB")
        self.statusBar().addPermanentWidget(self.memory_status)

        # Timer to update memory summary
        self.memory_timer = QTimer(self)
        self.memory_timer.timeout.connect(self.update_memory_status)
        self.memory_timer.start(2000)  # every 2 seconds

        # Window flags (PyQt6 enum style)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)
        self.setWindowFlag(Qt.WindowType.WindowMinimizeButtonHint, True)

        # Prevent double shutdown
        self._shutdown_called = False

    # ------------------------------------------------------------
    # Router Debug Panel
    # ------------------------------------------------------------
    def _create_router_debug_panel(self):
        group = QGroupBox("Router Debug")
        layout = QVBoxLayout()

        self.router_debug_text = QTextEdit()
        self.router_debug_text.setReadOnly(True)
        self.router_debug_text.setStyleSheet(
            "font-family: monospace; font-size: 12px;"
        )

        layout.addWidget(self.router_debug_text)
        group.setLayout(layout)
        return group

    def update_router_debug(self, info: dict):
        """Update the Router Debug panel with routing info."""
        try:
            pretty = json.dumps(info, indent=2)
        except Exception:
            pretty = str(info)
        self.router_debug_text.setText(pretty)

    # ------------------------------------------------------------
    # Memory summary updater
    # ------------------------------------------------------------
    def update_memory_status(self):
        try:
            snap = get_unified_memory_snapshot()
            used = snap["derived"]["used_mb_est"]
            self.memory_status.setText(f"Memory: {used:.1f} MB")
        except Exception:
            self.memory_status.setText("Memory: error")

    # ------------------------------------------------------------
    # Auto-unload writing model on close
    # ------------------------------------------------------------
    def closeEvent(self, event):
        if not self._shutdown_called:
            self._shutdown_called = True
            try:
                send_message("/unload_writing", bypass_memory=True)
            except Exception:
                pass

        super().closeEvent(event)
        print("GUI: closeEvent triggered")
