# src/gui/__main__.py

import sys
from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow
from ingestion.background import start_background_ingestion
import ingestion.vector_store

print(">>> GUI is using vector_store at:", ingestion.vector_store.__file__)


def main() -> None:
    # Start the ingestion daemon BEFORE launching the GUI
    start_background_ingestion()

    # No QtWebEngine.initialize() needed in PyQt6

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
