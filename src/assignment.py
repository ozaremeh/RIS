# src/assignment.py

from typing import List, Dict

from config import PROJECTS, TAU_EXCL, MODEL_ID
from classifier import classifier_scores, reasoning_type, topic_label
from memory_store import log_message


def current_model_id() -> str:
    return MODEL_ID


def _sigma_assign(scores: List[float]) -> List[int]:
    """
    Sigma-style assignment:
    - Take all projects whose score >= TAU_EXCL
    - If none meet the threshold, fall back to the single best project
    """
    if not scores:
        return []

    eligible = [i for i, s in enumerate(scores) if s >= TAU_EXCL]

    if not eligible:
        best = max(range(len(scores)), key=lambda i: scores[i])
        return [best]

    return eligible


def assign_projects(message: str) -> (List[int], Dict[int, float]):
    """
    Classify the message into projects, apply sigma assignment,
    log the message to memory, and return (assigned_indices, weights).
    """
    # Raw classifier scores per project index
    scores = classifier_scores(message)

    # Sigma assignment
    assigned = _sigma_assign(scores)

    # Weights for assigned projects (raw scores for now)
    weights: Dict[int, float] = {i: float(scores[i]) for i in assigned}

    # Metadata for logging
    rtype = reasoning_type(message)
    tlabel = topic_label(message)
    model_id = current_model_id()

    # Log to memory (this also updates the vector store)
    log_message(
        text=message,
        scores_raw=scores,
        assigned=assigned,
        weights=weights,
        reasoning_type=rtype,
        topic=tlabel,
        model_id=model_id,
    )

    return assigned, weights

