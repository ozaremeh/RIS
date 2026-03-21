# src/ingestion/watcher.py

from __future__ import annotations
import time
from pathlib import Path
from typing import Callable, Optional

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from ingestion.pipeline import PaperIngestionPipeline


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


class IngestionEventHandler(FileSystemEventHandler):
    """
    Handles filesystem events and triggers ingestion for new files.
    """

    def __init__(
        self,
        pipeline: PaperIngestionPipeline,
        progress_callback: Optional[Callable[[str], None]] = None,
    ):
        super().__init__()
        self.pipeline = pipeline
        self.progress_callback = progress_callback

    def on_created(self, event):
        if event.is_directory:
            return

        path = Path(event.src_path)
        ext = path.suffix.lower()

        if ext not in SUPPORTED_EXTENSIONS:
            return

        # Notify
        if self.progress_callback:
            self.progress_callback(f"Detected new file: {path.name}")

        # Give the OS a moment to finish writing the file
        time.sleep(0.5)

        # Ingest
        try:
            self.pipeline.ingest(str(path), progress_callback=self.progress_callback)
        except Exception as e:
            if self.progress_callback:
                self.progress_callback(f"Error ingesting {path.name}: {e}")
            else:
                print(f"[Watcher] Error ingesting {path}: {e}")


class FolderWatcher:
    """
    Watches a folder for new scientific papers and ingests them automatically.
    """

    def __init__(
        self,
        folder: str,
        pipeline: Optional[PaperIngestionPipeline] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
    ):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)

        self.pipeline = pipeline or PaperIngestionPipeline()
        self.progress_callback = progress_callback

        self.observer = Observer()

    def start(self):
        if self.progress_callback:
            self.progress_callback(f"Watching folder: {self.folder}")

        event_handler = IngestionEventHandler(
            pipeline=self.pipeline,
            progress_callback=self.progress_callback,
        )

        self.observer.schedule(event_handler, str(self.folder), recursive=False)
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join()
