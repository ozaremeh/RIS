# src/classifier.py

from typing import List
import numpy as np

from config import PROJECTS, PROJECT_DESCRIPTIONS
from embeddings import embed_text, cosine_similarity


# -------------------------------------------------------------------
# Precompute embeddings for project descriptions
# -------------------------------------------------------------------

# PROJECTS is an ordered list of project names.
# PROJECT_DESCRIPTIONS maps each project name → semantic description.
# We embed each description once at import time.
PROJECT_EMBEDS = {
    project: embed_text(PROJECT_DESCRIPTIONS[project])
    for project in PROJECTS
}


# -------------------------------------------------------------------
# Embedding-based project classifier
# -------------------------------------------------------------------

def classifier_scores(message: str) -> List[float]:
    msg_emb = embed_text(message)

    scores = []
    for project in PROJECTS:
        proj_emb = PROJECT_EMBEDS[project]
        sim = cosine_similarity(msg_emb, proj_emb)
        score = (sim + 1.0) / 2.0
        scores.append(score)

    # --- Domain keyword override ---
    text = message.lower()
    if "epha2" in text or "eph a2" in text:
        scores[PROJECTS.index("research")] += 0.5

    print("DEBUG:", list(zip(PROJECTS, scores)))
    return scores



# -------------------------------------------------------------------
# Reasoning type classifier (stub)
# -------------------------------------------------------------------

def reasoning_type(message: str) -> str:
    """
    Very simple keyword-based reasoning classifier.
    """
    text = message.lower()

    if any(w in text for w in ["prove", "equation", "derivative", "jacobian"]):
        return "mathematical"

    if any(w in text for w in ["code", "bug", "error", "stack trace"]):
        return "code"

    if any(w in text for w in ["design", "architecture", "pipeline"]):
        return "system_design"

    return "conceptual"


# -------------------------------------------------------------------
# Topic classifier (stub)
# -------------------------------------------------------------------

def topic_label(message: str) -> str:
    """
    Placeholder topic classifier.
    """
    return "general"
