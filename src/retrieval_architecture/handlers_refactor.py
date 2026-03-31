# retrieval_architecture/handlers_refactor.py

from architecture import load_refactoring_suggestions
from retrieval_architecture.memory_manager import (
    update_memory_with_suggestions,
)


# ------------------------------------------------------------
# Refactor suggestions
# ------------------------------------------------------------

def handle_refactor_query(prompt: str):
    suggestions = load_refactoring_suggestions()

    # Update refactor-aware memory with current suggestions
    update_memory_with_suggestions(suggestions)

    if not suggestions:
        return {"refactoring": ["No refactoring suggestions found."]}

    lower = prompt.lower()
    n = 5
    for word in lower.split():
        if word.isdigit():
            n = int(word)
            break

    top = suggestions[:n]
    return {"refactoring": [_format_single_suggestion(s) for s in top]}


def _format_single_suggestion(s: dict) -> str:
    if s["type"] == "large_module":
        return (
            f"Large module: {s['module']} ({s['loc']} LOC, {s['functions']} functions). "
            f"{s['suggestion']}"
        )
    if s["type"] == "high_coupling":
        return (
            f"High coupling: {s['module']} imports {s['imports']} modules. "
            f"{s['suggestion']}"
        )
    if s["type"] == "circular_dependency":
        a, b = s["modules"]
        return f"Circular dependency: {a} ↔ {b}. {s['suggestion']}"
    if s["type"] == "dead_code":
        return f"Dead code: {s['function']} is never called. {s['suggestion']}"
    if s["type"] == "complex_function":
        return (
            f"Complex function: {s['function']} (complexity {s['complexity']}). "
            f"{s['suggestion']}"
        )
    return str(s)


# ------------------------------------------------------------
# Explanation
# ------------------------------------------------------------

def handle_explain_query(prompt: str):
    suggestions = load_refactoring_suggestions()
    lower = prompt.lower()

    index = None
    for word in lower.split():
        if word.isdigit():
            index = int(word) - 1
            break

    if index is not None and 0 <= index < len(suggestions):
        return {"explanation": _explain_single_suggestion(suggestions[index])}

    for s in suggestions:
        if s.get("module") and s["module"].lower() in lower:
            return {"explanation": _explain_single_suggestion(s)}
        if s.get("function") and s["function"].lower() in lower:
            return {"explanation": _explain_single_suggestion(s)}

    return {"error": "Could not determine which suggestion to explain."}


def _explain_single_suggestion(s: dict) -> str:
    if s["type"] == "large_module":
        return (
            f"Module '{s['module']}' is large ({s['loc']} LOC, {s['functions']} functions). "
            "Large modules accumulate multiple responsibilities, making them harder to maintain."
        )
    if s["type"] == "high_coupling":
        return (
            f"Module '{s['module']}' imports {s['imports']} modules. "
            "High coupling makes the system brittle and hard to refactor."
        )
    if s["type"] == "circular_dependency":
        a, b = s["modules"]
        return (
            f"Modules '{a}' and '{b}' import each other. "
            "Circular dependencies complicate testing and import order."
        )
    if s["type"] == "dead_code":
        return (
            f"Function '{s['function']}' is never called. "
            "Dead code increases maintenance burden."
        )
    if s["type"] == "complex_function":
        return (
            f"Function '{s['function']}' has high cyclomatic complexity. "
            "Breaking it into helpers improves readability."
        )
    return "No detailed explanation available."


# ------------------------------------------------------------
# Apply refactor (patch)
# ------------------------------------------------------------

def handle_apply_refactor_query(prompt: str):
    suggestions = load_refactoring_suggestions()
    lower = prompt.lower()

    index = None
    for word in lower.split():
        if word.isdigit():
            index = int(word) - 1
            break

    if index is None or index >= len(suggestions):
        return {"error": "Could not determine which refactor to apply."}

    return {"patch": _generate_patch_for_suggestion(suggestions[index])}


def _generate_patch_for_suggestion(s: dict) -> str:
    if s["type"] == "large_module":
        return (
            f"Suggested patch for splitting module '{s['module']}':\n"
            f"1. Identify responsibility clusters.\n"
            f"2. Create new modules.\n"
            f"3. Move related functions.\n"
            f"4. Update imports.\n"
        )
    if s["type"] == "circular_dependency":
        a, b = s["modules"]
        return (
            f"Break circular dependency between {a} and {b}:\n"
            f"1. Extract shared logic.\n"
            f"2. Create shared module.\n"
            f"3. Update imports.\n"
        )
    if s["type"] == "high_coupling":
        return (
            f"Reduce coupling in '{s['module']}':\n"
            f"1. Remove unused imports.\n"
            f"2. Extract utilities.\n"
            f"3. Use dependency injection.\n"
        )
    if s["type"] == "complex_function":
        return (
            f"Simplify '{s['function']}':\n"
            f"1. Extract helper functions.\n"
            f"2. Reduce nesting.\n"
            f"3. Add docstrings.\n"
        )
    return "No patch available."


# ------------------------------------------------------------
# Refactor tasks
# ------------------------------------------------------------

def handle_refactor_task_query(prompt: str):
    suggestions = load_refactoring_suggestions()
    lower = prompt.lower()

    index = None
    for word in lower.split():
        if word.isdigit():
            index = int(word) - 1
            break

    if index is None or index >= len(suggestions):
        return {"error": "Could not determine which refactor to create a task for."}

    return {"task": _generate_task_for_suggestion(suggestions[index])}


def _generate_task_for_suggestion(s: dict) -> str:
    if s["type"] == "large_module":
        return (
            f"Refactoring Task: Split '{s['module']}'\n"
            f"Goal: Improve cohesion.\n"
            f"Steps:\n"
            f"  1. Identify responsibility clusters.\n"
            f"  2. Create new modules.\n"
            f"  3. Move functions.\n"
            f"  4. Update imports.\n"
            f"Verification: No import errors.\n"
        )
    if s["type"] == "circular_dependency":
        a, b = s["modules"]
        return (
            f"Refactoring Task: Break circular dependency {a} ↔ {b}\n"
            f"Steps:\n"
            f"  1. Extract shared logic.\n"
            f"  2. Create shared module.\n"
            f"  3. Update imports.\n"
        )
    if s["type"] == "high_coupling":
        return (
            f"Refactoring Task: Reduce coupling in '{s['module']}'\n"
            f"Steps:\n"
            f"  1. Remove unused imports.\n"
            f"  2. Extract utilities.\n"
            f"  3. Use dependency injection.\n"
        )
    if s["type"] == "complex_function":
        return (
            f"Refactoring Task: Simplify '{s['function']}'\n"
            f"Steps:\n"
            f"  1. Extract helpers.\n"
            f"  2. Reduce nesting.\n"
            f"  3. Add docstrings.\n"
        )
    return "No task available."
