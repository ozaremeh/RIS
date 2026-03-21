# src/embeddings.py

import numpy as np
import hashlib

EMBED_DIM = 128


def _hash_to_seed(text: str) -> int:
    """
    Convert text into a deterministic integer seed using SHA256.
    """
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(h[:8], 16)


def embed_text(text: str) -> np.ndarray:
    """
    Deterministic pseudo-embedding for now.
    Produces a stable vector for the same text across runs.
    """
    seed = _hash_to_seed(text)
    rng = np.random.default_rng(seed)
    vec = rng.normal(0, 1, EMBED_DIM)
    return vec / np.linalg.norm(vec)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Compute cosine similarity between two vectors.
    """
    num = float(np.dot(a, b))
    den = float(np.linalg.norm(a) * np.linalg.norm(b) + 1e-8)
    return num / den

