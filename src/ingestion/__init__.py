import os
from pathlib import Path

BASE_DIR = Path.home() / "ResearchPapers"
INCOMING_DIR = BASE_DIR / "incoming"
PROCESSED_DIR = BASE_DIR / "processed"
FAILED_DIR = BASE_DIR / "failed"

for d in [INCOMING_DIR, PROCESSED_DIR, FAILED_DIR]:
    os.makedirs(d, exist_ok=True)
