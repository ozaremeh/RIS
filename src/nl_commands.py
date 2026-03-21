# src/nl_commands.py

from __future__ import annotations

from typing import List, Dict
import re

from semantic_memory import add_semantic_fact
from semantic_memory import _load_semantic_entries, _save_semantic_entries  # type: ignore


# ---------------------------------------------------------------------
# Pending medium-confidence facts (for confirmation flow)
# ---------------------------------------------------------------------

PENDING_FACTS: List[str] = []


def set_pending_facts(facts: List[str]) -> None:
    """
    Store medium-confidence facts that need user confirmation.
    """
    global PENDING_FACTS
    PENDING_FACTS = list(facts)


def clear_pending_facts() -> None:
    global PENDING_FACTS
    PENDING_FACTS = []


# ---------------------------------------------------------------------
# Helpers for semantic memory manipulation
# ---------------------------------------------------------------------

def _list_all_semantic_facts() -> List[str]:
    entries = _load_semantic_entries()
    return [e.get("fact", "") for e in entries if e.get("fact")]


def _delete_fact_by_substring(fragment: str) -> bool:
    """
    Delete the first semantic fact that contains the given fragment.
    Returns True if something was deleted.
    """
    fragment = fragment.lower().strip()
    if not fragment:
        return False

    entries = _load_semantic_entries()
    new_entries = []
    deleted = False

    for e in entries:
        fact = e.get("fact", "")
        if not deleted and fragment in fact.lower():
            deleted = True
            continue
        new_entries.append(e)

    if deleted:
        _save_semantic_entries(new_entries)

    return deleted


def _update_fact_by_substring(old_fragment: str, new_fact: str) -> bool:
    """
    Update the first semantic fact that contains old_fragment to new_fact.
    Returns True if something was updated.
    """
    old_fragment = old_fragment.lower().strip()
    new_fact = new_fact.strip()
    if not old_fragment or not new_fact:
        return False

    entries = _load_semantic_entries()
    updated = False

    for e in entries:
        fact = e.get("fact", "")
        if not updated and old_fragment in fact.lower():
            e["fact"] = new_fact
            updated = True
            break

    if updated:
        _save_semantic_entries(entries)

    return updated


# ---------------------------------------------------------------------
# Pending-fact confirmation parsing (Option B)
# ---------------------------------------------------------------------

def _handle_pending_confirmation(user_message: str) -> str | None:
    """
    Handle user responses when there are pending medium-confidence facts.
    Supports:
      - yes / no
      - store all
      - store the first / second / third
      - store only specific ones by index words
    """
    global PENDING_FACTS
    if not PENDING_FACTS:
        return None

    text = user_message.lower()

    # Simple yes/no
    if "yes" in text and "no" not in text:
        for fact in PENDING_FACTS:
            add_semantic_fact(fact)
        count = len(PENDING_FACTS)
        clear_pending_facts()
        return f"Okay — I’ve stored {count} semantic fact(s) in long-term memory."

    if "no" in text and "yes" not in text:
        clear_pending_facts()
        return "Got it — I won’t store those semantic facts."

    # Selective storage
    indices_to_store: List[int] = []

    # Word-based indices
    if "first" in text:
        indices_to_store.append(0)
    if "second" in text:
        indices_to_store.append(1)
    if "third" in text:
        indices_to_store.append(2)

    # Numeric indices (e.g., "store 1 and 3")
    nums = re.findall(r"\b([1-9])\b", text)
    for n in nums:
        idx = int(n) - 1
        if idx not in indices_to_store:
            indices_to_store.append(idx)

    indices_to_store = [i for i in indices_to_store if 0 <= i < len(PENDING_FACTS)]

    if indices_to_store:
        stored_facts = []
        for i in indices_to_store:
            fact = PENDING_FACTS[i]
            add_semantic_fact(fact)
            stored_facts.append(fact)

        clear_pending_facts()
        joined = "\n".join(f"- {f}" for f in stored_facts)
        return (
            "Okay — I’ve stored the following semantic fact(s):\n"
            f"{joined}"
        )

    # If we reach here, we didn't understand the confirmation
    return (
        "I have some pending semantic facts, but I couldn’t understand your response.\n"
        "You can say things like:\n"
        "- Yes (store all)\n"
        "- No (store none)\n"
        "- Store the first one\n"
        "- Store 1 and 2\n"
    )


# ---------------------------------------------------------------------
# Explicit natural-language commands
# ---------------------------------------------------------------------

def _handle_add_fact_command(user_message: str) -> str | None:
    text = user_message.lower()

    # Patterns like:
    # "remember that ..."
    # "remember this: ..."
    # "store this as a fact: ..."
    # "add this to your long-term memory: ..."
    patterns = [
        "remember that",
        "remember this:",
        "remember this",
        "store this as a fact:",
        "store this as a fact",
        "add this to your long-term memory:",
        "add this to your long-term memory",
    ]

    for p in patterns:
        if p in text:
            idx = text.index(p) + len(p)
            fact = user_message[idx:].strip(" .:\n")
            if fact:
                add_semantic_fact(fact)
                return f"Got it — I’ll remember this as a semantic fact:\n- {fact}"
            else:
                return "I heard you ask me to remember something, but I couldn’t find the fact to store."

    return None


def _handle_list_facts_command(user_message: str) -> str | None:
    text = user_message.lower()

    triggers = [
        "what do you remember about me",
        "what do you remember of me",
        "show me your semantic memory",
        "list your long-term facts",
        "list your long term facts",
        "list semantic memory",
        "show semantic memory",
    ]

    if not any(t in text for t in triggers):
        return None

    facts = _list_all_semantic_facts()
    if not facts:
        return "I don’t have any semantic facts stored yet."

    lines = "\n".join(f"- {f}" for f in facts)
    return f"Here’s what I currently have in semantic memory:\n{lines}"


def _handle_forget_command(user_message: str) -> str | None:
    text = user_message.lower()

    if "forget" not in text and "delete" not in text and "remove" not in text:
        return None

    # Try to extract a fragment after the command word
    m = re.search(r"(forget|delete|remove)\s+(that|the fact about|the fact|this|.*)", text)
    fragment = ""
    if m:
        fragment = m.group(2)
        # If it's just "that" or "this", we don't know what to delete
        if fragment in {"that", "this"}:
            fragment = ""

    if not fragment.strip():
        return (
            "I heard you ask me to forget something, but I’m not sure which fact.\n"
            "You can say, for example: 'Forget the fact about my laptop.'"
        )

    success = _delete_fact_by_substring(fragment)
    if success:
        return f"Okay — I’ve removed the fact containing: '{fragment.strip()}'"
    else:
        return (
            "I couldn’t find any semantic fact matching that description.\n"
            "You can ask me to list my semantic memory to see what I know."
        )


def _handle_update_command(user_message: str) -> str | None:
    text = user_message.lower()

    if "update" not in text and "change" not in text:
        return None

    # Very simple pattern:
    # "update X to Y"
    # "change X to Y"
    m = re.search(r"(update|change)\s+(.*?)\s+to\s+(.*)", user_message, flags=re.IGNORECASE)
    if not m:
        return (
            "I heard you ask me to update a fact, but I couldn’t parse the request.\n"
            "Try something like: 'Update my laptop fact to I now use a 2024 MacBook Pro.'"
        )

    old_fragment = m.group(2).strip()
    new_fact = m.group(3).strip()

    if not old_fragment or not new_fact:
        return (
            "I need both what to update and what to change it to.\n"
            "For example: 'Update my laptop fact to I now use a 2024 MacBook Pro.'"
        )

    success = _update_fact_by_substring(old_fragment, new_fact)
    if success:
        return (
            "Okay — I’ve updated the semantic fact.\n"
            f"New fact:\n- {new_fact}"
        )
    else:
        return (
            "I couldn’t find any semantic fact matching that description.\n"
            "You can ask me to list my semantic memory to see what I know."
        )


# ---------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------

def handle_nl_command(user_message: str) -> str | None:
    """
    Try to interpret the user message as a natural-language command
    related to semantic memory.

    Order:
      1. Pending medium-confidence fact confirmation
      2. Explicit add-fact commands
      3. List semantic memory
      4. Forget fact
      5. Update fact

    Returns a reply string if a command was handled, otherwise None.
    """

    # 1. Pending confirmation
    if PENDING_FACTS:
        reply = _handle_pending_confirmation(user_message)
        if reply is not None:
            return reply

    # 2. Explicit add-fact command
    reply = _handle_add_fact_command(user_message)
    if reply is not None:
        return reply

    # 3. List semantic memory
    reply = _handle_list_facts_command(user_message)
    if reply is not None:
        return reply

    # 4. Forget fact
    reply = _handle_forget_command(user_message)
    if reply is not None:
        return reply

    # 5. Update fact
    reply = _handle_update_command(user_message)
    if reply is not None:
        return reply

    return None
