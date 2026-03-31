# src/orchestrator/semantic_manager.py

"""
Semantic memory manager.

Responsibilities:
- Extract semantic facts from user messages
- Build confirmation prompts (Phrasing C)
- Track pending facts awaiting confirmation
- Interpret user confirmation replies (yes/no/rewrite/partial)
- Store accepted facts in semantic memory
"""

from dataclasses import dataclass
from typing import List, Optional

from semantic_extractor import extract_and_store_facts
from semantic_memory import add_semantic_fact


@dataclass
class SemanticExtractionResult:
    """Returned after the assistant reply is generated."""
    has_facts: bool
    facts: List[str]
    confirmation_prompt: Optional[str]


@dataclass
class SemanticConfirmationResult:
    """Returned after the user responds to a semantic prompt."""
    stored_facts: List[str]
    ignored_facts: List[str]
    rewritten_fact: Optional[str]
    message_to_user: str


# ---------------------------------------------------------------------
# Pending semantic facts
# ---------------------------------------------------------------------

_pending_facts: List[str] = []


def set_pending_facts(facts: List[str]) -> None:
    global _pending_facts
    _pending_facts = list(facts)


def has_pending_facts() -> bool:
    return len(_pending_facts) > 0


def consume_pending_facts() -> List[str]:
    global _pending_facts
    facts = _pending_facts
    _pending_facts = []
    return facts


# ---------------------------------------------------------------------
# Extraction (post‑reply)
# ---------------------------------------------------------------------

def extract_facts_from_user_message(
    user_message: str,
    model_key: Optional[str] = None,
) -> SemanticExtractionResult:
    """
    Extract medium‑confidence semantic facts from the user message.
    Called AFTER the assistant reply is generated.

    NEW:
    Architecture model output should NEVER trigger semantic memory.
    """

    # ------------------------------------------------------------
    # NEW: Skip semantic memory for architecture model
    # ------------------------------------------------------------
    if model_key in ("architecture", "architecture_retriever"):
        return SemanticExtractionResult(
            has_facts=False,
            facts=[],
            confirmation_prompt=None,
        )

    # Normal semantic extraction
    facts = extract_and_store_facts(user_message)

    if not facts:
        return SemanticExtractionResult(
            has_facts=False,
            facts=[],
            confirmation_prompt=None,
        )

    # Build phrasing C
    if len(facts) == 1:
        prompt = f'Should I store this in semantic memory? → "{facts[0]}"'
    else:
        listed = "\n".join(f'- "{f}"' for f in facts)
        prompt = (
            "I found several possible semantic memories:\n"
            f"{listed}\n\n"
            "Which should I store? You may rewrite them or say 'no'."
        )

    return SemanticExtractionResult(
        has_facts=True,
        facts=facts,
        confirmation_prompt=prompt,
    )


# ---------------------------------------------------------------------
# Confirmation interpretation
# ---------------------------------------------------------------------

def interpret_confirmation_reply(
    user_reply: str,
    pending_facts: List[str],
) -> SemanticConfirmationResult:

    text = user_reply.strip().lower()

    yes_set = {"yes", "y", "sure", "ok", "okay", "yeah"}
    no_set = {"no", "n", "nope"}

    # YES → store all
    if text in yes_set:
        for f in pending_facts:
            add_semantic_fact(f)
        return SemanticConfirmationResult(
            stored_facts=pending_facts,
            ignored_facts=[],
            rewritten_fact=None,
            message_to_user="Stored.",
        )

    # NO → store none
    if text in no_set:
        return SemanticConfirmationResult(
            stored_facts=[],
            ignored_facts=pending_facts,
            rewritten_fact=None,
            message_to_user="Okay — I won’t store it.",
        )

    # PARTIAL ACCEPTANCE
    matched = []
    for f in pending_facts:
        if f.lower() in text:
            matched.append(f)

    if matched:
        for f in matched:
            add_semantic_fact(f)
        ignored = [f for f in pending_facts if f not in matched]
        return SemanticConfirmationResult(
            stored_facts=matched,
            ignored_facts=ignored,
            rewritten_fact=None,
            message_to_user="Stored the ones you indicated.",
        )

    # REWRITTEN FACT
    rewritten = user_reply.strip()
    if rewritten:
        add_semantic_fact(rewritten)
        return SemanticConfirmationResult(
            stored_facts=[rewritten],
            ignored_facts=pending_facts,
            rewritten_fact=rewritten,
            message_to_user="Stored your rewritten version.",
        )

    # Fallback
    return SemanticConfirmationResult(
        stored_facts=[],
        ignored_facts=pending_facts,
        rewritten_fact=None,
        message_to_user="Okay — I won’t store it.",
    )


# ---------------------------------------------------------------------
# High-level handler
# ---------------------------------------------------------------------

def handle_confirmation_reply(user_reply: str) -> Optional[SemanticConfirmationResult]:
    if not has_pending_facts():
        return None

    facts = consume_pending_facts()
    return interpret_confirmation_reply(user_reply, facts)
