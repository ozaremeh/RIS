# retrieval_architecture/memory_manager.py

import json
from pathlib import Path
from datetime import datetime

MEMORY_PATH = Path(__file__).parent / "memory.json"


def load_memory() -> dict:
    if not MEMORY_PATH.exists():
        return {}
    try:
        return json.loads(MEMORY_PATH.read_text())
    except Exception:
        return {}


def save_memory(mem: dict):
    MEMORY_PATH.write_text(json.dumps(mem, indent=2))


def _make_key(suggestion: dict) -> str:
    if suggestion["type"] == "large_module":
        return f"large_module:{suggestion['module']}"
    if suggestion["type"] == "high_coupling":
        return f"high_coupling:{suggestion['module']}"
    if suggestion["type"] == "circular_dependency":
        a, b = suggestion["modules"]
        return f"circular_dependency:{a}:{b}"
    if suggestion["type"] == "dead_code":
        return f"dead_code:{suggestion['function']}"
    if suggestion["type"] == "complex_function":
        return f"complex_function:{suggestion['function']}"
    return f"unknown:{suggestion}"


def update_memory_with_suggestions(suggestions: list[dict]):
    mem = load_memory()
    now = datetime.now().strftime("%Y-%m-%d")

    for s in suggestions:
        key = _make_key(s)

        if key not in mem:
            mem[key] = {
                "type": s["type"],
                "severity": s.get("severity", 0),
                "status": "unresolved",
                "first_detected": now,
                "last_seen": now,
            }
            if "module" in s:
                mem[key]["module"] = s["module"]
            if "function" in s:
                mem[key]["function"] = s["function"]
        else:
            # update last seen timestamp
            mem[key]["last_seen"] = now

    save_memory(mem)


def mark_resolved(key: str):
    mem = load_memory()
    if key in mem:
        mem[key]["status"] = "resolved"
        save_memory(mem)


def get_unresolved_issues() -> list[dict]:
    mem = load_memory()
    return [v for v in mem.values() if v["status"] == "unresolved"]


def get_architecture_history() -> dict:
    return load_memory()
