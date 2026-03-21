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
    """Returned after the user responds to a confirmation prompt."""
    stored_facts: List[str]
    ignored_facts: List[str]
    rewritten_fact: Optional[str]
    message_to_user: str


# ---------------------------------------------------------------------
# Pending semantic facts (awaiting user confirmation)
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

def extract_facts_from_user_message(user_message: str) -> SemanticExtractionResult:
    """
    Extract medium‑confidence semantic facts from the user message.
    This is called AFTER the assistant reply is generated.
    """
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
    """
    Interpret the user's reply to a semantic‑memory confirmation prompt.

    Supports:
    - yes / y / ok / sure → store all
    - no / n / nope → store none
    - rewritten fact → store rewritten version
    - partial acceptance → "store X", "only the first one", etc.
    """

    text = user_reply.strip().lower()

    yes_set = {"yes", "y", "sure", "ok", "okay", "yeah"}
    no_set = {"no", "n", "nope"}

    # 1. YES → store all pending facts
    if text in yes_set:
        for f in pending_facts:
            add_semantic_fact(f)
        return SemanticConfirmationResult(
            stored_facts=pending_facts,
            ignored_facts=[],
            rewritten_fact=None,
            message_to_user="Stored.",
        )

    # 2. NO → store nothing
    if text in no_set:
        return SemanticConfirmationResult(
            stored_facts=[],
            ignored_facts=pending_facts,
            rewritten_fact=None,
            message_to_user="Okay — I won’t store it.",
        )

    # 3. PARTIAL ACCEPTANCE (match original facts verbatim)
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

    # 4. REWRITTEN FACT
    rewritten = user_reply.strip()
    if rewritten:
        add_semantic_fact(rewritten)
        return SemanticConfirmationResult(
            stored_facts=[rewritten],
            ignored_facts=pending_facts,
            rewritten_fact=rewritten,
            message_to_user="Stored your rewritten version.",
        )

    # 5. Fallback — store nothing
    return SemanticConfirmationResult(
        stored_facts=[],
        ignored_facts=pending_facts,
        rewritten_fact=None,
        message_to_user="Okay — I won’t store it.",
    )


# ---------------------------------------------------------------------
# High-level handler for confirmation replies
# ---------------------------------------------------------------------

def handle_confirmation_reply(user_reply: str) -> Optional[SemanticConfirmationResult]:
    """
    Called when the user responds to a semantic-memory confirmation prompt.
    Returns None if there are no pending facts.
    """
    if not has_pending_facts():
        return None

    facts = consume_pending_facts()
    return interpret_confirmation_reply(user_reply, facts)
