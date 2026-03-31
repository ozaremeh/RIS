# src/ingestion/code_scanner.py

from dataclasses import dataclass
from pathlib import Path
import os
import time

EXCLUDED_DIRS = {
    "__pycache__",
    ".git",
    "venv",
    "env",
    ".idea",
    ".vscode",
    "research_memory.lancedb",
    "vector_store",
    "router_logs",
    "ingestion_cache",
}

ALLOWED_EXTENSIONS = {".py"}


@dataclass
class CodeFile:
    path: Path
    module: str
    size: int
    last_modified: float


def is_valid_file(path: Path) -> bool:
    """Return True if the file should be included in code ingestion."""
    if path.suffix not in ALLOWED_EXTENSIONS:
        return False
    return True


def scan_codebase(root: Path) -> list[CodeFile]:
    """
    Recursively scan the codebase starting at `root` and return a list of CodeFile objects.
    """
    code_files = []

    for dirpath, dirnames, filenames in os.walk(root):
        # Remove excluded directories from traversal
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]

        for filename in filenames:
            full_path = Path(dirpath) / filename

            if not is_valid_file(full_path):
                continue

            stat = full_path.stat()

            # Convert path to module-like dotted notation
            module = (
                full_path.relative_to(root)
                .with_suffix("")
                .as_posix()
                .replace("/", ".")
            )

            code_files.append(
                CodeFile(
                    path=full_path,
                    module=module,
                    size=stat.st_size,
                    last_modified=stat.st_mtime,
                )
            )

    return code_files
