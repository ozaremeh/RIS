# retrieval_architecture/router.py

from retrieval_architecture.handlers_refactor import (
    handle_refactor_query,
    handle_explain_query,
    handle_apply_refactor_query,
    handle_refactor_task_query,
)
from retrieval_architecture.handlers_code import (
    handle_show_code_query,
)
from retrieval_architecture.handlers_structure import (
    handle_structure_query,
)
from retrieval_architecture.memory_manager import (
    get_unresolved_issues,
)


# ------------------------------------------------------------
# Intent detection
# ------------------------------------------------------------

def is_explicit_refactor_query(q: str) -> bool:
    return any(k in q for k in [
        "refactor", "refactoring", "improve architecture",
        "clean up", "simplify", "too complex", "too large",
        "what should i refactor", "suggest improvements",
    ])


def is_implicit_refactor_query(q: str) -> bool:
    return any(k in q for k in [
        "messy", "confusing", "hard to follow", "too long",
        "too big", "too large", "bloated", "unwieldy",
        "cleanup", "clean up", "simplify", "architecture",
        "structure", "coupling", "complex", "why is this so",
        "why is this complicated",
    ])


def is_explain_query(q: str) -> bool:
    return any(k in q for k in ["explain", "why", "reason", "details"])


def is_show_code_query(q: str) -> bool:
    return any(k in q for k in ["show code", "open", "view code", "display code"])


def is_apply_refactor_query(q: str) -> bool:
    return any(k in q for k in ["apply", "fix", "implement", "patch"])


def is_refactor_task_query(q: str) -> bool:
    return any(k in q for k in [
        "task", "steps", "how do i", "walk me through",
        "guide me", "refactor this", "fix this", "how to fix",
    ])


def is_memory_query(q: str) -> bool:
    return any(k in q for k in [
        "unresolved issues",
        "architecture history",
        "what problems remain",
        "what should i fix next",
        "outstanding refactors",
        "pending refactors",
    ])


# ------------------------------------------------------------
# Main entry point
# ------------------------------------------------------------

def architecture_query(query: str):
    q = query.lower()

    # Memory / unresolved issues
    if is_memory_query(q):
        return {"unresolved": get_unresolved_issues()}

    # Implicit refactor routing
    if is_implicit_refactor_query(q):
        return handle_refactor_query(query)

    # Explicit refactor routing
    if is_explicit_refactor_query(q):
        return handle_refactor_query(query)

    # Explain refactor
    if is_explain_query(q):
        return handle_explain_query(query)

    # Show code
    if is_show_code_query(q):
        return handle_show_code_query(query)

    # Apply refactor
    if is_apply_refactor_query(q):
        return handle_apply_refactor_query(query)

    # Refactor tasks
    if is_refactor_task_query(q):
        return handle_refactor_task_query(query)

    # Structural queries (imports, calls, classes, functions, dependencies)
    return handle_structure_query(query)
