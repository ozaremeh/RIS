# src/reasoning/rag_engine.py

from __future__ import annotations
from typing import List, Dict, Any


class RAGEngine:
    """
    Retrieval-Augmented Generation engine for RIS.

    Responsibilities:
    - Embed user questions
    - Retrieve relevant chunks from the vector store
    - Build a structured scientific prompt
    - Call a reasoning LLM to synthesize an answer
    - Return answer + sources + raw chunks
    """

    def __init__(self, vector_store, embedder, llm):
        """
        vector_store: an instance of VectorStore
        embedder: an instance of Embedder (same one used for ingestion)
        llm: a reasoning-capable LLM client with a .generate(prompt: str) -> str API
        """
        self.vs = vector_store
        self.embedder = embedder
        self.llm = llm

    # ------------------------------------------------------------
    # Core RAG flow
    # ------------------------------------------------------------

    def retrieve(self, query: str, k: int = 20) -> List[Dict[str, Any]]:
        """
        Embed the query and retrieve top-k relevant chunks.
        """
        query_vec = self.embedder.embed([query])[0]
        hits = self.vs.search(query_vec, k=k)
        return hits

    # ------------------------------------------------------------
    # Metadata lookup helper
    # ------------------------------------------------------------

    def _lookup_metadata(self, paper_id: str) -> Dict[str, Any]:
        """
        Retrieve metadata for a paper_id from LanceDB.
        Returns a dict with title/authors/year/doi or fallback values.
        """
        rows = (
            self.vs.papers.search()
            .where(f"paper_id == '{paper_id}'")
            .limit(1)
            .to_list()
        )

        if not rows:
            return {
                "title": f"Paper {paper_id}",
                "authors": ["Unknown Authors"],
                "year": "n.d.",
                "doi": None,
            }

        meta = rows[0]
        return {
            "title": meta.get("title", "Unknown Title"),
            "authors": meta.get("authors", ["Unknown Authors"]),
            "year": meta.get("year", "n.d."),
            "doi": meta.get("doi", None),
        }

    # ------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------

    def build_prompt(self, query: str, hits: List[Dict[str, Any]]) -> str:
        """
        Build a structured scientific prompt from retrieved chunks.
        """
        if not hits:
            return f"""
You are RIS, a scientific reasoning assistant.

No relevant context was retrieved from the literature database.

Question:
{query}

Explain that no relevant papers were found, and suggest how the user might refine the query.
"""

        # Group chunks by paper_id
        by_paper: Dict[str, List[Dict[str, Any]]] = {}
        for h in hits:
            pid = h.get("paper_id", "unknown_paper")
            by_paper.setdefault(pid, []).append(h)

        context_blocks: List[str] = []

        for paper_id, chunks in by_paper.items():
            meta = self._lookup_metadata(paper_id)

            title = meta["title"]
            authors = ", ".join(meta["authors"])
            year = meta["year"]

            # Human-readable label
            label = f"{authors} ({year}) — {title}"

            # Sort chunks
            chunks_sorted = sorted(
                chunks,
                key=lambda c: c.get("chunk_index", 0)
            )

            paper_block_lines = [f"[{label}]"]

            for c in chunks_sorted:
                section = c.get("section", "")
                idx = c.get("chunk_index", 0)
                text = c.get("text", "")
                paper_block_lines.append(
                    f"(chunk {idx}, section: {section}) {text}"
                )

            context_blocks.append("\n".join(paper_block_lines))

        context = "\n\n".join(context_blocks)

        prompt = f"""
You are RIS, a scientific reasoning assistant.
You are given context from multiple scientific papers that have been ingested into a vector store.
Use ONLY the provided context to answer the question.

For each paper:
- summarize its key claims relevant to the question
- extract mechanisms, pathways, or hypotheses
- note any limitations or uncertainties

Then:
- compare and contrast findings across papers
- identify agreements, contradictions, or gaps
- synthesize a unified explanation
- propose next-step hypotheses grounded in the evidence

Cite papers using the human-readable labels already provided in brackets.

Context:
{context}

Question:
{query}

Answer with a concise, well-structured scientific response.
"""
        return prompt

    # ------------------------------------------------------------
    # Human-readable citation formatting
    # ------------------------------------------------------------

    def _format_sources(self, hits: List[Dict[str, Any]]) -> List[str]:
        """
        Convert paper_ids into human-readable citations using metadata.
        """
        sources = []
        seen = set()

        for h in hits:
            pid = h.get("paper_id")
            if not pid or pid in seen:
                continue
            seen.add(pid)

            meta = self._lookup_metadata(pid)

            title = meta["title"]
            authors = ", ".join(meta["authors"])
            year = meta["year"]
            doi = meta["doi"]

            if doi:
                citation = f"{authors} ({year}). {title}. DOI: {doi}"
            else:
                citation = f"{authors} ({year}). {title}"

            sources.append(citation)

        return sources

    # ------------------------------------------------------------
    # Full RAG pipeline
    # ------------------------------------------------------------

    def query(self, question: str, k: int = 20) -> Dict[str, Any]:
        """
        Full RAG pipeline:
        - retrieve relevant chunks
        - build prompt
        - call LLM
        - return answer + sources + raw chunks
        """
        hits = self.retrieve(question, k=k)
        prompt = self.build_prompt(question, hits)
        answer = self.llm.generate(prompt)

        # Human-readable citations
        sources = self._format_sources(hits)

        return {
            "answer": answer,
            "sources": sources,
            "chunks": hits,
        }
