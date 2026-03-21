# src/ingestion/chunker.py

from typing import List, Dict, Optional
import re
from dataclasses import dataclass

# If you later want to use a tokenizer (e.g., tiktoken or sentencepiece),
# you can plug it in here. For now, we use a simple whitespace tokenizer.


@dataclass
class Chunk:
    text: str
    chunk_index: int
    token_start: int
    token_end: int
    section: Optional[str] = None


# ------------------------------------------------------------
# Basic tokenization
# ------------------------------------------------------------

def simple_tokenize(text: str) -> List[str]:
    """Simple whitespace tokenizer."""
    return text.split()


def detokenize(tokens: List[str]) -> str:
    return " ".join(tokens)


# ------------------------------------------------------------
# Section detection (very simple v1 heuristic)
# ------------------------------------------------------------

SECTION_HEADERS = [
    "abstract",
    "introduction",
    "background",
    "methods",
    "materials and methods",
    "results",
    "discussion",
    "conclusion",
    "references",
]


def detect_section(line: str) -> Optional[str]:
    """Return section name if line looks like a section header."""
    clean = line.strip().lower()
    for header in SECTION_HEADERS:
        if clean.startswith(header):
            return header
    return None


# ------------------------------------------------------------
# Chunking logic
# ------------------------------------------------------------

def chunk_text(
    text: str,
    max_tokens: int = 512,
    overlap: int = 64,
    use_sections: bool = True,
) -> List[Chunk]:
    """
    Chunk text into overlapping token windows.
    Optionally track section boundaries using simple heuristics.
    """

    tokens = simple_tokenize(text)
    n = len(tokens)

    chunks: List[Chunk] = []
    current_section = None

    # Precompute section boundaries by scanning the text line-by-line
    if use_sections:
        section_map = {}
        running_token_index = 0

        for line in text.splitlines():
            sec = detect_section(line)
            if sec:
                section_map[running_token_index] = sec
                current_section = sec

            # Update token index by counting tokens in this line
            running_token_index += len(simple_tokenize(line))

    else:
        section_map = {}

    # Now create chunks
    chunk_index = 0
    i = 0

    while i < n:
        start = i
        end = min(i + max_tokens, n)

        # Determine section for this chunk
        section = None
        if use_sections:
            # Find the nearest section start <= start
            section_starts = [k for k in section_map.keys() if k <= start]
            if section_starts:
                nearest = max(section_starts)
                section = section_map[nearest]

        chunk_tokens = tokens[start:end]
        chunk_text = detokenize(chunk_tokens)

        chunks.append(
            Chunk(
                text=chunk_text,
                chunk_index=chunk_index,
                token_start=start,
                token_end=end,
                section=section,
            )
        )

        chunk_index += 1
        i += max_tokens - overlap

    return chunks
