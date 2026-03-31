# src/reasoning/literature_reasoner.py

from __future__ import annotations

from typing import List, Dict, Any

from api_client import call_model
from model_registry import get_model
from reasoning.rag_engine import RAGEngine
from ingestion.vector_store import VectorStore
from ingestion.embedder import Embedder


# ---------------------------------------------------------------------
# Local RAG engine for literature reasoning
# (reuses the same pattern as the main RAG engine)
# ---------------------------------------------------------------------

_VECTOR_STORE = VectorStore()
_EMBEDDER = Embedder()

_REASONING_MODEL_NAME = get_model("reasoning")["model_name"]

_LIT_RAG_ENGINE = RAGEngine(
    vector_store=_VECTOR_STORE,
    embedder=_EMBEDDER,
    llm=None,  # we only need retrieval here; reasoning is done below
)


# ---------------------------------------------------------------------
# System prompt for literature reasoning
# ---------------------------------------------------------------------

LITERATURE_REASONER_SYSTEM_PROMPT = """
You are a scientific literature reasoning assistant.

You receive:
- a research question
- excerpts from scientific papers (EVIDENCE)

You MUST:
1) Clearly distinguish between:
   - DIRECTLY SUPPORTED findings (explicit in the evidence)
   - PLAUSIBLE INFERENCES (consistent with evidence but not proven)
   - SPECULATIVE IDEAS (interesting but weakly supported)
2) Propose concrete, testable hypotheses.
3) Suggest specific follow-up experiments or analyses.
4) Avoid inventing data or claiming certainty where there is none.
5) When unsure, say so explicitly and explain what data would reduce uncertainty.
""".strip()


# ---------------------------------------------------------------------
# Helper: retrieve evidence chunks
# ---------------------------------------------------------------------

def _retrieve_evidence(question: str, top_k: int = 8) -> List[str]:
    """
    Retrieve relevant chunks from the literature store using the embedder.
    """
    # 1. Embed the question
    query_vec = _EMBEDDER.embed(question)

    # 2. Search the vector store
    results = _VECTOR_STORE.search(query_vec, k=top_k)

    # 3. Extract text fields
    chunks = []
    for r in results:
        text = r.get("text") or r.get("content") or ""
        if text:
            chunks.append(text)

    return chunks


# ---------------------------------------------------------------------
# Core entry point
# ---------------------------------------------------------------------

def run_literature_reasoner(user_question: str, top_k: int = 8) -> str:
    """
    Given a research question, retrieve relevant literature chunks and
    perform structured reasoning over them.

    Returns a single, structured text answer.
    """
    evidence_chunks = _retrieve_evidence(user_question, top_k=top_k)

    if not evidence_chunks:
        messages = [
            {"role": "system", "content": LITERATURE_REASONER_SYSTEM_PROMPT},
            {"role": "user", "content": (
                "RESEARCH QUESTION:\n"
                f"{user_question}\n\n"
                "No relevant evidence was retrieved from the literature store.\n"
                "Explain what kinds of papers or data would be needed to answer this question, "
                "and propose a few high-level hypotheses and experiments anyway, clearly marked as speculative."
            )},
        ]
        return call_model(_REASONING_MODEL_NAME, messages)

    evidence_text = "\n\n---\n\n".join(evidence_chunks)

    user_content = (
        "RESEARCH QUESTION:\n"
        f"{user_question}\n\n"
        "EVIDENCE FROM PAPERS (each block is from one or more papers):\n"
        f"{evidence_text}\n\n"
        "Now reason carefully. Structure your answer as:\n"
        "1) DIRECTLY SUPPORTED FINDINGS\n"
        "2) PLAUSIBLE INFERENCES\n"
        "3) SPECULATIVE IDEAS\n"
        "4) CONCRETE FOLLOW-UP EXPERIMENTS OR ANALYSES\n"
        "For each hypothesis or idea, briefly state what observation would support it and what would weaken it."
    )

    messages = [
        {"role": "system", "content": LITERATURE_REASONER_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    return call_model(_REASONING_MODEL_NAME, messages)
