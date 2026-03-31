import json
import os
from datetime import datetime, timedelta
from typing import List, Dict

EPISODIC_MEMORY_PATH = "episodic_memory.jsonl"


# ------------------------------------------------------------
# Store an episode
# ------------------------------------------------------------
def store_episode(role: str, content: str) -> None:
    """
    Append a single conversational turn to episodic memory.
    """
    episode = {
        "timestamp": datetime.utcnow().isoformat(),
        "role": role,
        "content": content,
    }

    with open(EPISODIC_MEMORY_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(episode) + "\n")


# ------------------------------------------------------------
# Load all episodes
# ------------------------------------------------------------
def load_all_episodes() -> List[Dict]:
    if not os.path.exists(EPISODIC_MEMORY_PATH):
        return []

    episodes = []
    with open(EPISODIC_MEMORY_PATH, "r", encoding="utf-8") as f:
        for line in f:
            try:
                episodes.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return episodes


# ------------------------------------------------------------
# Retrieve relevant episodes
# ------------------------------------------------------------
def retrieve_episodic_memory(query: str, limit: int = 5) -> List[Dict]:
    """
    Very simple relevance scoring:
    - keyword overlap
    - recency weighting
    """
    episodes = load_all_episodes()
    query_lower = query.lower()

    scored = []
    for ep in episodes:
        content = ep.get("content", "").lower()

        # keyword match
        score = 0
        for word in query_lower.split():
            if word in content:
                score += 1

        # recency weighting (last 7 days)
        try:
            ts = datetime.fromisoformat(ep["timestamp"])
            age_days = (datetime.utcnow() - ts).days
            if age_days < 7:
                score += 1
        except Exception:
            pass

        if score > 0:
            scored.append((score, ep))

    # sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)

    return [ep for score, ep in scored[:limit]]


# ------------------------------------------------------------
# Prune old episodes (optional)
# ------------------------------------------------------------
def prune_old_episodes(days: int = 30) -> None:
    """
    Keep only the last N days of episodes.
    """
    episodes = load_all_episodes()
    cutoff = datetime.utcnow() - timedelta(days=days)

    new_eps = []
    for ep in episodes:
        try:
            ts = datetime.fromisoformat(ep["timestamp"])
            if ts >= cutoff:
                new_eps.append(ep)
        except Exception:
            continue

    with open(EPISODIC_MEMORY_PATH, "w", encoding="utf-8") as f:
        for ep in new_eps:
            f.write(json.dumps(ep) + "\n")
