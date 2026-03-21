# src/memory_store.py

from typing import List, Dict
from dataclasses import dataclass, asdict
from vector_store import VECTOR_STORE
import time
import orjson
import os

MEMORY_FILE = "memory_log.jsonl"


# -----------------------------
# Memory Entry Dataclass
# -----------------------------
@dataclass
class MemoryEntry:
    text: str
    scores_raw: List[float]
    assigned: List[int]
    weights: Dict[int, float]          # internal: int keys
    reasoning_type: str
    topic: str
    timestamp: float
    model_id: str


# -----------------------------
# In-memory log
# -----------------------------
MEMORY_LOG: List[MemoryEntry] = []


# -----------------------------
# Disk I/O
# -----------------------------
def _load_memory_from_disk():
    """Load all memory entries from disk and rebuild the vector store."""
    global MEMORY_LOG

    if not os.path.exists(MEMORY_FILE):
        return

    with open(MEMORY_FILE, "rb") as f:
        for line in f:
            if not line.strip():
                continue

            data = orjson.loads(line)

            # Convert weight keys back to ints
            if "weights" in data:
                data["weights"] = {int(k): v for k, v in data["weights"].items()}

            entry = MemoryEntry(**data)
            MEMORY_LOG.append(entry)

            # Rebuild vector store
            VECTOR_STORE.add_entry(entry)


def _append_to_disk(entry: MemoryEntry):
    """Append a single entry to the JSONL log."""
    data = asdict(entry)

    # Convert weight keys to strings for JSON
    data["weights"] = {str(k): v for k, v in data["weights"].items()}

    with open(MEMORY_FILE, "ab") as f:
        f.write(orjson.dumps(data))
        f.write(b"\n")


# -----------------------------
# Public API
# -----------------------------
def init_memory():
    """Load memory from disk and rebuild vector store."""
    _load_memory_from_disk()


def log_message(
    text: str,
    scores_raw: List[float],
    assigned: List[int],
    weights: Dict[int, float],
    reasoning_type: str,
    topic: str,
    model_id: str,
):
    """Create a new memory entry, store it in RAM, persist it, and index it."""
    entry = MemoryEntry(
        text=text,
        scores_raw=scores_raw,
        assigned=assigned,
        weights=weights,  # internal: int keys
        reasoning_type=reasoning_type,
        topic=topic,
        timestamp=time.time(),
        model_id=model_id,
    )

    # 1. Add to in-memory log
    MEMORY_LOG.append(entry)

    # 2. Add to vector store
    VECTOR_STORE.add_entry(entry)

    # 3. Persist to disk
    _append_to_disk(entry)

    return entry

