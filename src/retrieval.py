# src/retrieval.py

from typing import List
import time

from memory_store import MemoryEntry
from vector_store import VECTOR_STORE
from config import (
    ALPHA,
    BETA,
    GAMMA,
    DELTA,
    SIM_GAMMA,
    RECENCY_ETA,
    TOP_K,
)


def _now() -> float:
    return time.time()


def _power_law_recency(age: float) -> float:
    return 1.0 / ((1.0 + age) ** RECENCY_ETA)


def _score_entry(
    entry: MemoryEntry,
    sim: float,
    target_project: int,
) -> float:
    # Normalize similarity [-1,1] → [0,1]
    sim01 = (sim + 1.0) / 2.0
    sim_term = sim01 ** SIM_GAMMA

    age = _now() - entry.timestamp
    recency_term = _power_law_recency(age)

    w = entry.weights.get(target_project, 0.0)

    return (
        ALPHA * sim_term +
        BETA * recency_term +
        DELTA * sim_term * w
    )


def retrieve_relevant_chunks(
    query: str,
    target_project: int,
    k: int = TOP_K,
) -> List[MemoryEntry]:

    sims = VECTOR_STORE.search(query, k=50)
    if not sims:
        return []

    scored = []
    for entry, sim in sims:
        s = _score_entry(entry, sim, target_project)
        scored.append((entry, s))

    scored.sort(key=lambda x: x[1], reverse=True)

    # Duplicate suppression
    seen = set()
    unique = []

    for entry, _ in scored:
        key = entry.text.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(entry)
        if len(unique) >= k:
            break

    return unique
