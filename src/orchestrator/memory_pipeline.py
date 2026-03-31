"""
Memory pipeline for the orchestrator.

Responsibilities:
- Handle semantic confirmation replies
- Handle memory mode commands (expanded/minimal/conservative)
- Handle explicit /memory commands (list/search/forget/clean)
- Handle natural-language memory commands
- Decide whether the message is fully handled by memory logic
"""

from dataclasses import dataclass
from typing import Optional

from nl_commands import handle_nl_command
from memory import log_message
from orchestrator.logging import log_event

import orchestrator.semantic_manager as semantic_manager
from orchestrator.memory_cleaner import handle_memory_command


@dataclass
class MemoryPipelineResult:
    intercepted: bool        # True if memory pipeline handled the message
    reply: Optional[str]     # Assistant reply (if intercepted)


def maybe_handle_memory_mode_command(user_message: str, retrieval_mode_ref) -> Optional[str]:
    """
    Handles commands like:
      - "expanded memory"
      - "minimal memory"
      - "default memory"
    """
    text = user_message.lower()

    if "expanded memory" in text or "search deeper" in text or "use more memory" in text:
        retrieval_mode_ref["mode"] = "expanded"
        log_event("Retrieval mode changed", {"mode": "expanded"})
        return "Okay — I’ll retrieve more distant or lower-similarity memories for future messages."

    if "minimal memory" in text or "ignore memory" in text or "no memory for this" in text:
        retrieval_mode_ref["mode"] = "minimal"
        log_event("Retrieval mode changed", {"mode": "minimal"})
        return "Understood — I’ll use minimal or no long-term memory for future messages."

    if "default memory" in text or "conservative memory" in text or "normal memory" in text:
        retrieval_mode_ref["mode"] = "conservative"
        log_event("Retrieval mode changed", {"mode": "conservative"})
        return "Memory retrieval set back to conservative mode."

    return None


def process_memory_pipeline(
    user_message: str,
    retrieval_mode_ref: dict,
) -> MemoryPipelineResult:
    """
    Runs the memory pipeline:
      0. Semantic confirmation replies
      1. Memory mode commands
      2. /memory commands
      3. Natural-language memory commands

    Returns a MemoryPipelineResult.
    """

    # 0. Semantic confirmation replies (highest priority)
    if semantic_manager.has_pending_facts():
        result = semantic_manager.handle_confirmation_reply(user_message)
        if result is not None:
            log_message("user", user_message)
            log_message("assistant", result.message_to_user)
            return MemoryPipelineResult(
                intercepted=True,
                reply=result.message_to_user,
            )

    # 1. Memory mode commands
    mode_reply = maybe_handle_memory_mode_command(user_message, retrieval_mode_ref)
    if mode_reply is not None:
        log_message("user", user_message)
        log_message("assistant", mode_reply)
        return MemoryPipelineResult(
            intercepted=True,
            reply=mode_reply,
        )

    # 2. Explicit /memory commands (list/search/forget/clean)
    memory_cmd_reply = handle_memory_command(user_message)
    if memory_cmd_reply is not None:
        log_event("Handled /memory command", {})
        log_message("user", user_message)
        log_message("assistant", memory_cmd_reply)
        return MemoryPipelineResult(
            intercepted=True,
            reply=memory_cmd_reply,
        )

    # 3. Natural-language memory commands
    nl_reply = handle_nl_command(user_message)
    if nl_reply is not None:
        log_event("Handled natural-language memory command", {})
        log_message("user", user_message)
        log_message("assistant", nl_reply)
        return MemoryPipelineResult(
            intercepted=True,
            reply=nl_reply,
        )

    return MemoryPipelineResult(
        intercepted=False,
        reply=None,
    )
