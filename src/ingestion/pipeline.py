# src/ingestion/pipeline.py

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Callable
from pathlib import Path

from ingestion.vector_store import VectorStore, VectorStoreConfig
from ingestion.extract_text import extract_text
from ingestion.extract_metadata import extract_metadata
from ingestion.chunker import chunk_text
from ingestion.code_chunker import chunk_code_ast
from ingestion.embedder import Embedder, EmbeddingModelConfig
from ingestion.code_scanner import scan_codebase


# ------------------------------------------------------------
# Configuration dataclass
# ------------------------------------------------------------

@dataclass
class PipelineConfig:
    """
    Configuration for the ingestion pipeline.
    All mutable defaults must use default_factory.
    """
    vector_store: VectorStoreConfig = field(default_factory=VectorStoreConfig)
    embedder: EmbeddingModelConfig = field(default_factory=EmbeddingModelConfig)
    max_tokens: int = 512
    overlap: int = 64
    use_sections: bool = True


# ------------------------------------------------------------
# Main ingestion pipeline
# ------------------------------------------------------------

class PaperIngestionPipeline:
    """
    Orchestrates ingestion of:
    - scientific papers (PDFs, text docs)
    - RIS's own codebase (Python files)
    """

    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config if config is not None else PipelineConfig()

        # Initialize vector store + embedder
        self.vs = VectorStore(self.config.vector_store)
        self.embedder = Embedder(self.config.embedder)

    # --------------------------------------------------------
    # Paper ingestion
    # --------------------------------------------------------

    def ingest(self, path: str, progress_callback: Optional[Callable[[str], None]] = None):
        """
        Ingest a single scientific paper.
        progress_callback(msg) is called at each step (optional).
        """

        def log(msg: str):
            print(f"[Pipeline] {msg}")
            if progress_callback:
                progress_callback(msg)

        path_obj = Path(path)
        if not path_obj.exists():
            raise FileNotFoundError(f"File not found: {path}")

        log(f"Starting ingestion: {path_obj.name}")

        # --------------------------------------------------------
        # Step 1: Extract text
        # --------------------------------------------------------
        log("Extracting text...")
        text = extract_text(path)

        # --------------------------------------------------------
        # Step 2: Extract metadata
        # --------------------------------------------------------
        log("Extracting metadata...")
        metadata = extract_metadata(path, text=text)

        # Duplicate detection
        if self.vs.paper_exists(metadata["file_hash"]):
            log("Paper already ingested (duplicate detected). Skipping.")
            return {
                "status": "duplicate",
                "paper_id": metadata["file_hash"],
                "metadata": metadata,
            }

        # Insert paper row
        log("Inserting paper metadata...")
        paper_id = self.vs.insert_paper(metadata)

        # --------------------------------------------------------
        # Step 3: Chunking
        # --------------------------------------------------------
        log("Chunking text...")
        chunks = chunk_text(
            text,
            max_tokens=self.config.max_tokens,
            overlap=self.config.overlap,
            use_sections=self.config.use_sections,
        )

        log(f"Created {len(chunks)} chunks.")

        # --------------------------------------------------------
        # Step 4: Embedding
        # --------------------------------------------------------
        log("Embedding chunks...")
        chunk_texts = [c.text for c in chunks]
        embeddings = self.embedder.embed(chunk_texts)

        # --------------------------------------------------------
        # Step 5: Store in vector DB
        # --------------------------------------------------------
        log("Storing chunks in vector store...")
        self.vs.insert_chunks(paper_id, chunks, embeddings)

        log("Ingestion complete.")

        return {
            "status": "success",
            "paper_id": paper_id,
            "metadata": metadata,
            "num_chunks": len(chunks),
        }

    # --------------------------------------------------------
    # Code ingestion
    # --------------------------------------------------------

    def ingest_codebase(self, root: Optional[str] = None, progress_callback: Optional[Callable[[str], None]] = None):
        """
        Ingest RIS's own codebase:
        - scan for .py files
        - chunk code (code-aware)
        - embed chunks
        - store in vector DB
        """

        def log(msg: str):
            print(f"[CodeIngest] {msg}")
            if progress_callback:
                progress_callback(msg)

        # Default root = src/
        root_path = Path(root) if root else Path(__file__).parent.parent

        log(f"Scanning codebase at: {root_path}")

        # Step 1: Scan for code files
        files = scan_codebase(root_path)
        log(f"Found {len(files)} code files.")

        all_chunks = []
        for f in files:
            log(f"Chunking {f.module}...")

            try:
                text = f.path.read_text(encoding="utf-8", errors="ignore")
            except Exception as e:
                log(f"Failed to read {f.path}: {e}")
                continue

            # Code-aware chunking
            chunks = chunk_code_ast(
                text=text,
                module=f.module,
                max_tokens=self.config.max_tokens,
                overlap=self.config.overlap,
            )

            # Attach metadata
            for c in chunks:
                c.metadata = {
                    "type": "code",
                    "module": f.module,
                    "path": str(f.path),
                }
                c.metadata["block_type"] = c.block_type
                c.metadata["name"] = c.name


            all_chunks.extend(chunks)

        log(f"Created {len(all_chunks)} code chunks.")

        # Step 2: Embed
        log("Embedding code chunks...")
        chunk_texts = [c.text for c in all_chunks]
        embeddings = self.embedder.embed(chunk_texts)

        # Step 3: Store
        log("Storing code chunks in vector store...")
        self.vs.insert_code_chunks(all_chunks, embeddings)

        log("Code ingestion complete.")

        return {
            "status": "success",
            "files": len(files),
            "chunks": len(all_chunks),
        }