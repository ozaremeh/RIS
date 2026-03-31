# src/semantic_memory.py

from __future__ import annotations

from typing import Dict, List, Tuple
from pathlib import Path
import json
import datetime


# ---------------------------------------------------------------------
# Paths and basic config
# ---------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SEMANTIC_MEMORY_PATH = PROJECT_ROOT / "semantic_memory.jsonl"

# Semantic memory decays MUCH slower than episodic memory
DAILY_DECAY_RATE = 0.995          # very slow decay
REINFORCEMENT_AMOUNT = 0.20       # stronger reinforcement than episodic
MIN_WEIGHT = 0.10                 # semantic facts rarely drop below this

# ---------------------------------------------------------------------
# Utility: load + save
# ---------------------------------------------------------------------

def _load_semantic_entries() -> List[Dict]:
    if not SEMANTIC_MEMORY_PATH.exists():
        return []

    entries: List[Dict] = []
    with SEMANTIC_MEMORY_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)

                # Backward compatibility
                if "weight" not in entry:
                    entry["weight"] = 1.0
                if "tags" not in entry:
                    entry["tags"] = []

                entries.append(entry)
            except json.JSONDecodeError:
                continue

    return entries


def _save_semantic_entries(entries: List[Dict]) -> None:
    with SEMANTIC_MEMORY_PATH.open("w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

print("Semantic memory writing to:", SEMANTIC_MEMORY_PATH)

# ---------------------------------------------------------------------
# Decay
# ---------------------------------------------------------------------

def _apply_decay(entry: Dict) -> None:
    """
    Apply slow decay to semantic memory.
    """
    timestamp = entry.get("timestamp")
    if not timestamp:
        return

    try:
        t = datetime.datetime.fromisoformat(timestamp)
    except Exception:
        return

    now = datetime.datetime.now()
    days_old = (now - t).days

    if days_old <= 0:
        return

    entry["weight"] *= (DAILY_DECAY_RATE ** days_old)

    if entry["weight"] < MIN_WEIGHT:
        entry["weight"] = MIN_WEIGHT


# ---------------------------------------------------------------------
# Adding semantic facts
# ---------------------------------------------------------------------

def add_semantic_fact(fact: str, tags: List[str] | None = None) -> None:
    """
    Add a stable fact to semantic memory.
    Facts are stored with a weight and optional tags.
    """
    SEMANTIC_MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "fact": fact,
        "tags": tags or [],
        "weight": 1.0,
    }

    with SEMANTIC_MEMORY_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------

def _tokenize(text: str) -> List[str]:
    return [t for t in text.lower().split() if t]


def _jaccard_similarity(a: List[str], b: List[str]) -> float:
    set_a = set(a)
    set_b = set(b)
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def retrieve_semantic_memory(query: str, k: int = 3) -> List[str]:
    """
    Retrieve the most relevant semantic facts.
    Always returns the top-k weighted matches.
    """

    entries = _load_semantic_entries()
    if not entries:
        return []

    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    scored: List[Tuple[float, Dict]] = []

    for entry in entries:
        _apply_decay(entry)

        fact = entry.get("fact", "")
        tokens = _tokenize(fact)
        sim = _jaccard_similarity(query_tokens, tokens)

        score = sim * entry["weight"]
        scored.append((score, entry))

    # Sort by weighted score
    scored.sort(key=lambda x: x[0], reverse=True)

    # Select top-k
    selected = [entry for _, entry in scored[:k] if entry["weight"] > MIN_WEIGHT]

    # Reinforce selected facts
    for entry in selected:
        entry["weight"] += REINFORCEMENT_AMOUNT

    # Save updated weights
    _save_semantic_entries(entries)

    # Return formatted facts
    return [entry["fact"] for entry in selected]


# ---------------------------------------------------------------------
# Management helpers: list / remove / update
# ---------------------------------------------------------------------

def list_semantic_facts() -> List[str]:
    """
    Return all semantic facts (ignoring very low-weight ones).
    """
    entries = _load_semantic_entries()
    return [
        e.get("fact", "")
        for e in entries
        if e.get("fact") and e.get("weight", 0.0) >= MIN_WEIGHT
    ]


def remove_semantic_fact(match_substring: str) -> List[str]:
    """
    Remove any facts whose text contains the given substring (case-insensitive).
    Returns the list of removed facts.
    """
    match_substring = match_substring.lower().strip()
    if not match_substring:
        return []

    entries = _load_semantic_entries()
    kept: List[Dict] = []
    removed: List[str] = []

    for e in entries:
        fact = e.get("fact", "")
        if match_substring in fact.lower():
            removed.append(fact)
        else:
            kept.append(e)

    if removed:
        _save_semantic_entries(kept)

    return removed


def update_semantic_fact(old_substring: str, new_fact: str) -> List[str]:
    """
    Update any facts whose text contains old_substring to new_fact.
    Returns the list of updated (new) facts.
    """
    old_substring = old_substring.lower().strip()
    new_fact = new_fact.strip()
    if not old_substring or not new_fact:
        return []

    entries = _load_semantic_entries()
    updated: List[str] = []

    for e in entries:
        fact = e.get("fact", "")
        if old_substring in fact.lower():
            e["fact"] = new_fact
            updated.append(new_fact)

    if updated:
        _save_semantic_entries(entries)

    return updated
