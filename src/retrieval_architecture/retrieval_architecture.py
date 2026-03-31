# src/retrieval_architecture.py

from __future__ import annotations
from typing import Dict, List
from pathlib import Path
import ast
import json

from architecture import (
    load_architecture_graph,
    load_call_graph,
    load_module_metrics,
    load_refactoring_suggestions,
)


# ------------------------------------------------------------
# Safety wrapper
# ------------------------------------------------------------

def _safe(result):
    """
    Ensure the result is JSON-serializable.
    If not, convert all nested objects to strings.
    """
    try:
        json.dumps(result, default=str)
        return result
    except Exception:
        return json.loads(json.dumps(result, default=str))


# ------------------------------------------------------------
# Load graph once per session
# ------------------------------------------------------------

_graph_cache = None

def get_graph():
    global _graph_cache
    if _graph_cache is None:
        _graph_cache = load_architecture_graph()
    return _graph_cache


# ------------------------------------------------------------
# Query helpers
# ------------------------------------------------------------

def find_importers(target_module: str) -> List[str]:
    graph = get_graph()
    return [
        mod for mod, deps in graph.items()
        if target_module in deps.imports
    ]


def find_callers(function_name: str) -> List[str]:
    graph = get_graph()
    return [
        mod for mod, deps in graph.items()
        if function_name in deps.calls
    ]


def list_classes(module: str) -> List[str]:
    graph = get_graph()
    if module in graph:
        return sorted(graph[module].classes)
    return []


def list_functions(module: str) -> List[str]:
    graph = get_graph()
    if module in graph:
        return sorted(graph[module].functions)
    return []


def module_dependencies(module: str) -> Dict:
    graph = get_graph()
    if module not in graph:
        return {}
    deps = graph[module]
    return {
        "imports": sorted(deps.imports),
        "classes": sorted(deps.classes),
        "functions": sorted(deps.functions),
        "calls": sorted(deps.calls),
    }


# ------------------------------------------------------------
# NL intent detection
# ------------------------------------------------------------

def is_refactor_query(q: str) -> bool:
    return any(k in q for k in [
        "refactor", "refactoring", "improve architecture",
        "clean up", "simplify", "too complex", "too large",
        "what should i refactor", "suggest improvements",
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


# ------------------------------------------------------------
# Refactoring suggestion handler
# ------------------------------------------------------------

def handle_refactor_query(prompt: str) -> Dict:
    suggestions = load_refactoring_suggestions()

    if not suggestions:
        return _safe({"refactoring": ["No refactoring suggestions found."]})

    # detect "top N"
    lower = prompt.lower()
    n = 5
    for word in lower.split():
        if word.isdigit():
            n = int(word)
            break

    top = suggestions[:n]
    formatted = [_format_single_suggestion(s) for s in top]
    return _safe({"refactoring": formatted})


def _format_single_suggestion(s: Dict) -> str:
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
# Explanation handler
# ------------------------------------------------------------

def handle_explain_query(prompt: str) -> Dict:
    suggestions = load_refactoring_suggestions()
    lower = prompt.lower()

    # detect "explain N"
    index = None
    for word in lower.split():
        if word.isdigit():
            index = int(word) - 1
            break

    if index is not None and 0 <= index < len(suggestions):
        return _safe({"explanation": _explain_single_suggestion(suggestions[index])})

    # fallback: match module/function name
    for s in suggestions:
        if s.get("module") and s["module"].lower() in lower:
            return _safe({"explanation": _explain_single_suggestion(s)})
        if s.get("function") and s["function"].lower() in lower:
            return _safe({"explanation": _explain_single_suggestion(s)})

    return _safe({"error": "Could not determine which suggestion to explain."})


def _explain_single_suggestion(s: Dict) -> str:
    if s["type"] == "large_module":
        return (
            f"Module '{s['module']}' is large ({s['loc']} LOC, {s['functions']} functions). "
            "Large modules accumulate multiple responsibilities, making them harder to maintain, "
            "test, and reason about. Splitting it improves cohesion and reduces cognitive load."
        )

    if s["type"] == "high_coupling":
        return (
            f"Module '{s['module']}' imports {s['imports']} modules. "
            "High coupling means changes ripple across the system, making refactoring difficult."
        )

    if s["type"] == "circular_dependency":
        a, b = s["modules"]
        return (
            f"Modules '{a}' and '{b}' import each other. This creates fragile import order, "
            "complicates testing, and often indicates shared logic that should be extracted."
        )

    if s["type"] == "dead_code":
        return (
            f"Function '{s['function']}' is never called. Dead code increases maintenance burden "
            "and should be removed unless it represents an unimplemented feature."
        )

    if s["type"] == "complex_function":
        return (
            f"Function '{s['function']}' has cyclomatic complexity {s['complexity']}. "
            "High complexity indicates deeply nested logic or many branches. "
            "Extracting helper functions improves readability and testability."
        )

    return "No detailed explanation available."


# ------------------------------------------------------------
# Show code handler
# ------------------------------------------------------------

def handle_show_code_query(prompt: str) -> Dict:
    lower = prompt.lower()

    # detect module
    if "module" in lower:
        name = lower.split("module")[-1].strip()
        path = _module_to_path(name)
        if path and path.exists():
            return _safe({"code": path.read_text()})
        return _safe({"error": f"Module '{name}' not found."})

    # detect function
    for token in lower.split():
        if "." in token:
            return _safe({"code": _extract_function_code(token)})

    return _safe({"error": "Could not determine which code to show."})


def _module_to_path(module: str) -> Path | None:
    root = Path(__file__).parent
    parts = module.split(".")
    path = root.joinpath(*parts).with_suffix(".py")
    return path if path.exists() else None


def _extract_function_code(fq_name: str) -> str:
    if "." not in fq_name:
        return f"Invalid function name '{fq_name}'."

    module, func = fq_name.rsplit(".", 1)
    path = _module_to_path(module)
    if not path:
        return f"Module '{module}' not found."

    text = path.read_text()
    tree = ast.parse(text)
    lines = text.splitlines()

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func:
            start = node.lineno - 1
            end = getattr(node, "end_lineno", start)
            return "\n".join(lines[start:end])

    return f"Function '{func}' not found in module '{module}'."


# ------------------------------------------------------------
# Apply refactor handler
# ------------------------------------------------------------

def handle_apply_refactor_query(prompt: str) -> Dict:
    suggestions = load_refactoring_suggestions()
    lower = prompt.lower()

    # detect "apply N"
    index = None
    for word in lower.split():
        if word.isdigit():
            index = int(word) - 1
            break

    if index is None or index >= len(suggestions):
        return _safe({"error": "Could not determine which refactor to apply."})

    s = suggestions[index]
    return _safe({"patch": _generate_patch_for_suggestion(s)})


def _generate_patch_for_suggestion(s: Dict) -> str:
    if s["type"] == "large_module":
        return (
            f"Suggested patch for splitting module '{s['module']}':\n\n"
            f"1. Identify responsibility clusters.\n"
            f"2. Create new modules (e.g., {s['module']}_io.py, {s['module']}_logic.py).\n"
            f"3. Move related functions into each new module.\n"
            f"4. Update imports in dependent modules.\n"
        )

    if s["type"] == "circular_dependency":
        a, b = s["modules"]
        return (
            f"Suggested patch for breaking circular dependency between {a} and {b}:\n\n"
            f"1. Identify shared logic.\n"
            f"2. Create new module '{a}_shared.py'.\n"
            f"3. Move shared functions there.\n"
            f"4. Update imports in both modules.\n"
        )

    if s["type"] == "high_coupling":
        return (
            f"Suggested patch for reducing coupling in '{s['module']}':\n\n"
            f"1. Identify unused imports.\n"
            f"2. Extract shared utilities into a new module.\n"
            f"3. Replace direct imports with dependency injection.\n"
        )

    if s["type"] == "complex_function":
        return (
            f"Suggested patch for simplifying '{s['function']}':\n\n"
            f"1. Identify logical blocks.\n"
            f"2. Extract each block into a helper function.\n"
            f"3. Replace nested logic with early returns.\n"
        )

    return "No patch available for this suggestion."


# ------------------------------------------------------------
# Refactoring task handler
# ------------------------------------------------------------

def handle_refactor_task_query(prompt: str) -> Dict:
    suggestions = load_refactoring_suggestions()
    lower = prompt.lower()

    # detect "task for N"
    index = None
    for word in lower.split():
        if word.isdigit():
            index = int(word) - 1
            break

    if index is None or index >= len(suggestions):
        return _safe({"error": "Could not determine which refactor to create a task for."})

    s = suggestions[index]
    return _safe({"task": _generate_task_for_suggestion(s)})


def _generate_task_for_suggestion(s: Dict) -> str:
    if s["type"] == "large_module":
        return (
            f"Refactoring Task: Split large module '{s['module']}'\n\n"
            f"Goal:\n"
            f"  Reduce module size and improve cohesion.\n\n"
            f"Why this matters:\n"
            f"  Large modules accumulate multiple responsibilities, making them harder to test and maintain.\n\n"
            f"Steps:\n"
            f"  1. Identify responsibility clusters inside '{s['module']}'.\n"
            f"  2. Create new modules (e.g., {s['module']}_io.py, {s['module']}_logic.py).\n"
            f"  3. Move related functions into each new module.\n"
            f"  4. Update imports in dependent modules.\n"
            f"  5. Run the test suite or manual checks.\n\n"
            f"Verification:\n"
            f"  - No import errors.\n"
            f"  - Code paths still execute correctly.\n"
            f"  - Module responsibilities are clearer.\n"
        )

    if s["type"] == "circular_dependency":
        a, b = s["modules"]
        return (
            f"Refactoring Task: Break circular dependency between {a} and {b}\n\n"
            f"Goal:\n"
            f"  Remove the import cycle and improve module independence.\n\n"
            f"Why this matters:\n"
            f"  Circular dependencies create fragile import order and complicate testing.\n\n"
            f"Steps:\n"
            f"  1. Identify functions or classes used by both modules.\n"
            f"  2. Create a new shared module (e.g., {a}_shared.py).\n"
            f"  3. Move shared logic into the new module.\n"
            f"  4. Update imports in both {a} and {b}.\n"
            f"  5. Verify that neither module imports the other.\n\n"
            f"Verification:\n"
            f"  - No circular imports.\n"
            f"  - Shared logic is isolated.\n"
        )

    if s["type"] == "high_coupling":
        return (
            f"Refactoring Task: Reduce coupling in '{s['module']}'\n\n"
            f"Goal:\n"
            f"  Lower the number of imports and improve modularity.\n\n"
            f"Why this matters:\n"
            f"  High coupling makes the system brittle and hard to refactor.\n\n"
            f"Steps:\n"
            f"  1. Identify unused imports.\n"
            f"  2. Extract shared utilities into a new module.\n"
            f"  3. Replace direct imports with dependency injection where possible.\n"
            f"  4. Update dependent modules.\n\n"
            f"Verification:\n"
            f"  - Fewer imports.\n"
            f"  - No broken dependencies.\n"
        )

    if s["type"] == "complex_function":
        return (
            f"Refactoring Task: Simplify complex function '{s['function']}'\n\n"
            f"Goal:\n"
            f"  Reduce cyclomatic complexity and improve readability.\n\n"
            f"Why this matters:\n"
            f"  Complex functions are harder to test and maintain.\n\n"
            f"Steps:\n"
            f"  1. Identify logical blocks inside the function.\n"
            f"  2. Extract each block into a helper function.\n"
            f"  3. Replace nested logic with early returns.\n"
            f"  4. Add docstrings to clarify behavior.\n\n"
            f"Verification:\n"
            f"  - Lower complexity score.\n"
            f"  - Function is easier to read.\n"
        )

    return "No task available for this suggestion."


# ------------------------------------------------------------
# Main entry point
# ------------------------------------------------------------

def architecture_query(query: str) -> Dict:
    """
    Natural-language-ish interface for architecture introspection.
    """

    q = query.lower()

    # Refactoring tasks
    if is_refactor_task_query(q):
        return handle_refactor_task_query(query)

    # Refactoring suggestions
    if is_refactor_query(q):
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

    # "who imports X"
    if q.startswith("who imports "):
        mod = q.replace("who imports ", "").strip()
        return _safe({"importers": find_importers(mod)})

    # "who calls X"
    if q.startswith("who calls "):
        fn = q.replace("who calls ", "").strip()
        return _safe({"callers": find_callers(fn)})

    # "list classes in X"
    if q.startswith("list classes in "):
        mod = q.replace("list classes in ", "").strip()
        return _safe({"classes": list_classes(mod)})

    # "list functions in X"
    if q.startswith("list functions in "):
        mod = q.replace("list functions in ", "").strip()
        return _safe({"functions": list_functions(mod)})

    # "show dependencies for X"
    if q.startswith("show dependencies for "):
        mod = q.replace("show dependencies for ", "").strip()
        return _safe(module_dependencies(mod))

    return _safe({"error": "Unrecognized architecture query"})
