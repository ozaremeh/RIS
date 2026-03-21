# src/vector_store.py

from typing import List, Tuple, TYPE_CHECKING
import numpy as np

from embeddings import embed_text

if TYPE_CHECKING:
    from memory_store import MemoryEntry


class VectorStore:
    def __init__(self):
        self.embeddings: List[np.ndarray] = []
        self.entries: List["MemoryEntry"] = []

    def add_entry(self, entry: "MemoryEntry"):
        emb = embed_text(entry.text)
        self.embeddings.append(emb)
        self.entries.append(entry)

    def search(self, query: str, k: int = 5) -> List[Tuple["MemoryEntry", float]]:
        if not self.entries:
            return []

        q_emb = embed_text(query)
        sims = []

        for emb, entry in zip(self.embeddings, self.entries):
            num = float(np.dot(q_emb, emb))
            den = float(np.linalg.norm(q_emb) * np.linalg.norm(emb) + 1e-8)
            sim = num / den
            sims.append((entry, sim))

        sims.sort(key=lambda x: x[1], reverse=True)
        return sims[:k]


VECTOR_STORE = VectorStore()

