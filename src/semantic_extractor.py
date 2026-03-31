from __future__ import annotations

from typing import List, Dict
import json
import re
import unicodedata

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
    "- a durable characteristic or identity\n"
    "- something that will still matter in future conversations\n\n"
    "Do NOT extract:\n"
    "- temporary feelings\n"
    "- momentary states ('I'm tired')\n"
    "- jokes, hypotheticals, or sarcasm\n"
    "- one-off events\n"
    "- questions\n"
    "- statements about the current conversation\n"
    "- scientific facts, lab protocols, or domain knowledge\n"
    "- statements about biology, chemistry, physics, or technical workflows\n"
    "- any statement not explicitly about the user\n\n"
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
# JSON extraction helper
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
# Guardrails and heuristics
# ---------------------------------------------------------------------

ARCHITECTURE_TERMS = [
    "architecture", "module", "import", "dependency", "dependencies",
    "router", "executor", "rag", "vector store", "embedder",
    "retrieval", "pipeline", "call graph", "class list", "function list",
    "code", "bug", "error", "stack trace",
]

QUESTION_WORDS = [
    "what", "why", "how", "when", "where", "who", "should", "can", "could",
    "would", "is it", "are you", "do you", "did you",
]

DECLARATIVE_PATTERNS = [
    "i am", "i prefer", "i like", "i dislike", "i enjoy",
    "my goal is", "my goals are", "i want to", "i plan to",
    "i always", "i never", "i tend to",
]

SCIENCE_TERMS = [
    "pcr", "reaction", "plasmid", "dna", "rna", "protein", "enzyme",
    "polymerase", "buffer", "mgcl2", "primer", "anneal", "cycle",
    "genome", "gene", "mutation", "assay", "culture", "ligase",
    "restriction", "vector", "transfection", "epha2", "mapk",
    "signaling", "pathway", "kinase", "phosphorylation",
]

SCIENCE_NUMBER_PATTERN = re.compile(
    r"\b\d+\s*(ul|ml|nm|mm|um|µl|µm)\b",
    re.IGNORECASE,
)


def _normalize(s: str) -> str:
    """Normalize Unicode (µ → u, etc.) and strip accents."""
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")


def _contains_science_terms(message: str) -> bool:
    lower = _normalize(message.lower())
    tokens = re.findall(r"[a-z0-9]+", lower)

    if any(term in tokens for term in SCIENCE_TERMS):
        return True

    if SCIENCE_NUMBER_PATTERN.search(lower):
        return True

    return False


def _looks_declarative(message: str) -> bool:
    """Return True only if the message looks like a stable declarative fact."""
    lower = message.lower().strip()

    if not any(p in lower for p in DECLARATIVE_PATTERNS):
        return False

    if lower.endswith("?"):
        return False

    return True


def _contains_architecture_terms(message: str) -> bool:
    lower = message.lower()
    return any(term in lower for term in ARCHITECTURE_TERMS)


def _looks_like_question(message: str) -> bool:
    lower = message.lower().strip()
    if lower.endswith("?"):
        return True
    return any(lower.startswith(w) for w in QUESTION_WORDS)


# ---------------------------------------------------------------------
# Explicit /remember command
# ---------------------------------------------------------------------

def handle_remember_command(message: str) -> str | None:
    """
    If the message starts with /remember, store the remainder as a semantic fact.
    Returns the stored fact if successful, otherwise None.
    """
    lower = message.lower().strip()
    if not lower.startswith("/remember"):
        return None

    fact = message[len("/remember"):].strip()
    if not fact:
        return None

    add_semantic_fact(fact)
    return fact


# ---------------------------------------------------------------------
# Hybrid policy
# ---------------------------------------------------------------------

def extract_and_store_facts(message: str, model_key: str | None = None) -> List[str]:
    """
    Extract semantic facts and apply hybrid policy:
    - HIGH → auto-store
    - MEDIUM → return for confirmation
    - LOW → ignore

    Architecture model output should NEVER be processed for semantic memory.
    """

    stripped = message.strip()

    # 0. Explicit /remember command bypasses everything
    stored = handle_remember_command(message)
    if stored is not None:
        return [f"__REMEMBERED__::{stored}"]

    # 1. Skip all other slash-commands (/memory, /unload_writing, etc.)
    if stripped.startswith("/"):
        return []

    # 2. Scientific content is never semantic memory
    if _contains_science_terms(message):
        return []

    # 3. Skip architecture/system messages entirely
    if model_key in ("architecture", "architecture_retriever"):
        return []

    if _contains_architecture_terms(message):
        return []

    # 4. Skip questions and meta-conversation
    if _looks_like_question(message):
        return []

    # 5. Only extract from declarative, stable-looking statements
    if not _looks_declarative(message):
        return []

    # 6. Run the extractor
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
