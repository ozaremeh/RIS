# src/orchestrator/history.py
"""
Conversation history management for the orchestrator.

Responsibilities:
- Maintain a global conversation history list
- Provide helper functions for appending and resetting
- Keep orchestrator.py clean and modular
"""

from typing import List, Dict
import datetime


# ---------------------------------------------------------------------
# Internal history store
# ---------------------------------------------------------------------

_CONVERSATION_HISTORY: List[Dict[str, str]] = []


# ---------------------------------------------------------------------
# Logging helper (local to history)
# ---------------------------------------------------------------------

def _log_event(event: str, data: Dict = None) -> None:
    timestamp = datetime.datetime.now().isoformat(timespec="seconds")
    print(f"[HISTORY {timestamp}] {event}")
    if data:
        for key, value in data.items():
            print(f"    {key}: {value}")


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------

def get_history() -> List[Dict[str, str]]:
    """Return the full conversation history."""
    return _CONVERSATION_HISTORY


def append_user_message(content: str) -> None:
    """Append a user message to the conversation history."""
    _CONVERSATION_HISTORY.append({"role": "user", "content": content})
    _log_event("Appended user message", {"content_preview": content[:120]})


def append_assistant_message(content: str) -> None:
    """Append an assistant message to the conversation history."""
    _CONVERSATION_HISTORY.append({"role": "assistant", "content": content})
    _log_event("Appended assistant message", {"content_preview": content[:120]})


def reset_history() -> None:
    """Clear the conversation history."""
    _CONVERSATION_HISTORY.clear()
    _log_event("Conversation history reset")
