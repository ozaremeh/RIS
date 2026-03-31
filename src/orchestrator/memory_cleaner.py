from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List, Optional, Tuple
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------
# Import the EXACT same semantic memory path used by semantic_memory.py
# ---------------------------------------------------------------------

from semantic_memory import SEMANTIC_MEMORY_PATH as MEMORY_PATH

print("Memory cleaner reading from:", MEMORY_PATH)


@dataclass
class SemanticFact:
    index: int
    timestamp: str
    fact: str
    tags: List[str]
    weight: float

# ---------------------------------------------------------------------
# Low-level load/save (JSONL)
# ---------------------------------------------------------------------

def _load_raw_memory() -> List[dict]:
    if not MEMORY_PATH.exists():
        return []

    items = []
    with MEMORY_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return items


def _save_raw_memory(items: List[dict]) -> None:
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MEMORY_PATH.open("w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------
# Convert to/from SemanticFact
# ---------------------------------------------------------------------

def _load_semantic_facts() -> List[SemanticFact]:
    raw = _load_raw_memory()
    facts: List[SemanticFact] = []
    for i, item in enumerate(raw):
        facts.append(
            SemanticFact(
                index=i,
                timestamp=item.get("timestamp", ""),
                fact=item.get("fact", ""),
                tags=item.get("tags", []) or [],
                weight=float(item.get("weight", 1.0)),
            )
        )
    return facts


def _save_semantic_facts(facts: List[SemanticFact]) -> None:
    raw: List[dict] = []
    for f in facts:
        raw.append(
            {
                "timestamp": f.timestamp or datetime.utcnow().isoformat(),
                "fact": f.fact,
                "tags": f.tags,
                "weight": f.weight,
            }
        )
    _save_raw_memory(raw)


# ---------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------

def _format_fact(f: SemanticFact) -> str:
    ts = f.timestamp or "unknown time"
    return f"[{f.index}] {f.fact}  (added: {ts})"


def _format_fact_list(facts: List[SemanticFact], header: str) -> str:
    if not facts:
        return f"{header}\n\nNo semantic facts found."
    lines = [header, ""]
    for f in facts:
        lines.append(_format_fact(f))
    return "\n".join(lines)


# ---------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------

def list_facts() -> str:
    facts = _load_semantic_facts()
    return _format_fact_list(facts, "Semantic memory facts:")


def search_facts(query: str) -> str:
    q = query.lower().strip()
    facts = _load_semantic_facts()
    matches = [f for f in facts if q in f.fact.lower()]
    return _format_fact_list(matches, f"Semantic memory facts matching '{query}':")


def forget_by_index(idx: int) -> str:
    facts = _load_semantic_facts()
    if idx < 0 or idx >= len(facts):
        return f"No fact found at index {idx}."

    removed = facts[idx]
    remaining = [f for f in facts if f.index != idx]

    # Reindex
    for i, f in enumerate(remaining):
        f.index = i

    _save_semantic_facts(remaining)
    return f"Removed semantic fact:\n{_format_fact(removed)}"


SCIENCE_TERMS = [
    "pcr", "reaction", "plasmid", "dna", "rna", "protein", "enzyme",
    "polymerase", "buffer", "mgcl2", "primer", "anneal", "cycle",
    "genome", "gene", "mutation", "assay", "culture", "ligase",
    "restriction", "vector", "transfection", "epha2", "mapk",
    "signaling", "pathway", "kinase", "phosphorylation",
]

ARCH_TERMS = [
    "architecture", "module", "import", "dependency", "dependencies",
    "router", "executor", "rag", "vector store", "embedder",
    "retrieval", "pipeline", "call graph", "class list", "function list",
    "code", "bug", "error", "stack trace",
]


def _clean_by_terms(terms: List[str]) -> Tuple[int, int]:
    facts = _load_semantic_facts()
    before = len(facts)
    remaining: List[SemanticFact] = []

    for f in facts:
        lower = f.fact.lower()
        if any(t in lower for t in terms):
            continue
        remaining.append(f)

    # Reindex
    for i, f in enumerate(remaining):
        f.index = i

    _save_semantic_facts(remaining)
    return before, len(remaining)


def clean_science() -> str:
    before, after = _clean_by_terms(SCIENCE_TERMS)
    removed = before - after
    return f"Cleaned semantic memory: removed {removed} science-related facts (remaining: {after})."


def clean_architecture() -> str:
    before, after = _clean_by_terms(ARCH_TERMS)
    removed = before - after
    return f"Cleaned semantic memory: removed {removed} architecture/system-related facts (remaining: {after})."


# ---------------------------------------------------------------------
# Command handler
# ---------------------------------------------------------------------

def handle_memory_command(message: str) -> Optional[str]:
    """
    Handle /memory commands.

    Supported:
      /memory list
      /memory search <keyword>
      /memory forget <index>
      /memory clean science
      /memory clean architecture
    """
    text = message.strip()
    lower = text.lower()

    if not lower.startswith("/memory"):
        return None

    parts = text.split(maxsplit=2)

    if len(parts) == 1:
        return (
            "Memory commands:\n"
            "- /memory list\n"
            "- /memory search <keyword>\n"
            "- /memory forget <index>\n"
            "- /memory clean science\n"
            "- /memory clean architecture"
        )

    cmd = parts[1].lower()

    if cmd == "list":
        return list_facts()

    if cmd == "search":
        if len(parts) < 3:
            return "Usage: /memory search <keyword>"
        return search_facts(parts[2])

    if cmd == "forget":
        if len(parts) < 3:
            return "Usage: /memory forget <index>"
        try:
            idx = int(parts[2])
        except ValueError:
            return "Index must be an integer, e.g. /memory forget 3"
        return forget_by_index(idx)

    if cmd == "clean":
        if len(parts) < 3:
            return "Usage: /memory clean <science|architecture>"
        target = parts[2].lower()
        if target == "science":
            return clean_science()
        if target == "architecture":
            return clean_architecture()
        return "Unknown clean target. Use: /memory clean science | /memory clean architecture"

    return "Unrecognized /memory command."
