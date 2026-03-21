# src/memory.py

import os
import json
import math
import datetime
from typing import List, Dict, Any

from config import PROJECT_ROOT
from embeddings import embed_text


# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

EPISODIC_MEMORY_PATH = os.path.join(
    PROJECT_ROOT, "data", "episodic_memory.jsonl"
)


# ---------------------------------------------------------------------
# Ensure directory exists
# ---------------------------------------------------------------------

os.makedirs(os.path.dirname(EPISODIC_MEMORY_PATH), exist_ok=True)


# ---------------------------------------------------------------------
# Utility: load and save JSONL
# ---------------------------------------------------------------------

def _load_episodic_entries() -> List[Dict[str, Any]]:
    if not os.path.exists(EPISODIC_MEMORY_PATH):
        return []
    entries = []
    with open(EPISODIC_MEMORY_PATH, "r", encoding="utf-8") as f:
        for line in f:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def _save_episodic_entries(entries: List[Dict[str, Any]]) -> None:
    with open(EPISODIC_MEMORY_PATH, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")


# ---------------------------------------------------------------------
# Cosine similarity
# ---------------------------------------------------------------------

def _cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


# ---------------------------------------------------------------------
# Decay function
# ---------------------------------------------------------------------

def _apply_decay(timestamp: str) -> float:
    """
    Compute a decay weight based on how old the memory is.
    Newer memories get weight ~1.0, older memories decay toward 0.
    """
    try:
        t = datetime.datetime.fromisoformat(timestamp)
    except Exception:
        return 1.0

    now = datetime.datetime.now()
    days = (now - t).days

    # Exponential decay: half-life ~30 days
    half_life = 30.0
    decay = 0.5 ** (days / half_life)
    return decay


# ---------------------------------------------------------------------
# Logging episodic memory
# ---------------------------------------------------------------------

def log_message(role: str, text: str) -> None:
    """
    Store a user or assistant message in episodic memory.
    Ensures embeddings are JSON-serializable.
    """
    raw_emb = embed_text(text)

    # Convert ndarray → list if needed
    if hasattr(raw_emb, "tolist"):
        embedding = raw_emb.tolist()
    else:
        embedding = raw_emb

    entry = {
        "role": role,
        "text": text,
        "embedding": embedding,
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
    }

    with open(EPISODIC_MEMORY_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------

def retrieve_relevant_memory(query: str, mode: str = "conservative") -> List[str]:
    """
    Retrieve episodic memories relevant to the query.
    Modes:
      - conservative: top 3, high similarity threshold
      - expanded: top 6, lower threshold
      - minimal: return []
    """

    if mode == "minimal":
        return []

    entries = _load_episodic_entries()
    if not entries:
        return []

    raw_query_emb = embed_text(query)
    query_emb = (
        raw_query_emb.tolist()
        if hasattr(raw_query_emb, "tolist")
        else raw_query_emb
    )

    scored = []
    for e in entries:
        emb = e.get("embedding")
        if not emb:
            continue

        sim = _cosine_similarity(query_emb, emb)
        decay = _apply_decay(e.get("timestamp", ""))

        score = sim * decay
        scored.append((score, e))

    scored.sort(key=lambda x: x[0], reverse=True)

    if mode == "conservative":
        top_n = 3
        threshold = 0.35
    else:  # expanded
        top_n = 6
        threshold = 0.15

    results = []
    for score, e in scored[:top_n]:
        if score < threshold:
            continue
        results.append(f"{e['role']}: {e['text']}")

    return results
