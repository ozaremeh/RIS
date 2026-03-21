# src/semantic_extractor.py

from __future__ import annotations

from typing import List, Dict
import json

from api_client import call_model
from config import ROUTER_MODEL
from semantic_memory import add_semantic_fact


# ---------------------------------------------------------------------
# Extraction prompt
# ---------------------------------------------------------------------

EXTRACTION_PROMPT = (
    "Extract stable, long-term semantic facts from the following user "
    "message.\n\n"
    "A 'semantic fact' is:\n"
    "- a stable preference\n"
    "- a personal detail that is unlikely to change\n"
    "- a long-term project or goal\n"
    "- a domain fact the user states as true\n"
    "- a durable characteristic or identity\n"
    "- something that will still matter in future conversations\n\n"
    "Do NOT extract:\n"
    "- temporary feelings\n"
    "- momentary states ('I'm tired')\n"
    "- jokes, hypotheticals, or sarcasm\n"
    "- one-off events\n"
    "- questions\n"
    "- statements about the current conversation\n\n"
    "For each fact you extract, classify it as:\n"
    "- HIGH: clearly stable and long-term\n"
    "- MEDIUM: possibly stable but uncertain\n"
    "- LOW: ephemeral or not a fact\n\n"
    "Return ONLY valid JSON in this format:\n\n"
    "[\n"
    "  {\"fact\": \"...\", \"confidence\": \"HIGH\"},\n"
    "  {\"fact\": \"...\", \"confidence\": \"MEDIUM\"}\n"
    "]\n"
)


# ---------------------------------------------------------------------
# JSON extraction helper (no regex, no escapes)
# ---------------------------------------------------------------------

def _safe_json_extract(text: str) -> List[Dict]:
    """Extract the first JSON array by manually scanning for brackets."""
    if not isinstance(text, str):
        return []

    start = None
    depth = 0

    for i, ch in enumerate(text):
        if ch == "[":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "]":
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    block = text[start : i + 1]
                    try:
                        parsed = json.loads(block)
                        if isinstance(parsed, list):
                            return parsed
                    except Exception:
                        pass

    return []


# ---------------------------------------------------------------------
# Core extraction
# ---------------------------------------------------------------------

def extract_semantic_facts(message: str) -> List[Dict]:
    """Call the extractor model to identify semantic facts."""
    prompt = EXTRACTION_PROMPT + "\nUSER MESSAGE:\n" + message + "\n"

    try:
        raw = call_model(
            ROUTER_MODEL,
            [
                {"role": "system", "content": "You extract semantic facts."},
                {"role": "user", "content": prompt},
            ],
        )
    except Exception:
        return []

    return _safe_json_extract(raw)


# ---------------------------------------------------------------------
# Hybrid policy
# ---------------------------------------------------------------------

def extract_and_store_facts(message: str) -> List[str]:
    """
    Extract semantic facts and apply hybrid policy:
    - HIGH → auto-store
    - MEDIUM → return for confirmation
    - LOW → ignore
    """
    extracted = extract_semantic_facts(message)
    if not extracted:
        return []

    medium: List[str] = []

    for item in extracted:
        fact = item.get("fact", "").strip()
        conf = item.get("confidence", "").upper().strip()

        if not fact:
            continue

        if conf == "HIGH":
            add_semantic_fact(fact)

        elif conf == "MEDIUM":
            medium.append(fact)

    return medium
