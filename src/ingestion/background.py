# src/ingestion/background.py

from threading import Thread
from pathlib import Path

from ingestion.watcher import FolderWatcher
from ingestion import INCOMING_DIR  # or wherever you defined your incoming folder


def start_background_ingestion() -> None:
    """
    Starts a daemon thread that watches the incoming folder
    and runs the ingestion pipeline on new PDFs.
    """
    def run():
        watcher = FolderWatcher(str(INCOMING_DIR))
        watcher.start()

    t = Thread(target=run, daemon=True)
    t.start()
