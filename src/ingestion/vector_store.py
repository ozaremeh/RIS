# src/ingestion/vector_store.py

from __future__ import annotations
from typing import List, Dict, Any
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import lancedb
import pyarrow as pa
from lancedb import vector  # <-- correct import for your version


# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

@dataclass
class VectorStoreConfig:
    db_path: str = "/Users/ozare/research-intelligence/research_memory.lancedb"
    papers_table: str = "papers"
    chunks_table: str = "chunks"


# ------------------------------------------------------------
# Vector Store Wrapper (Locked Schema)
# ------------------------------------------------------------

class VectorStore:
    def __init__(self, config: VectorStoreConfig = VectorStoreConfig()):
        self.config = config

        abs_path = Path(config.db_path).resolve()
        abs_path.parent.mkdir(parents=True, exist_ok=True)

        print(">>> LanceDB path:", config.db_path)
        print(">>> LanceDB absolute:", abs_path)

        self.db = lancedb.connect(str(abs_path))

        # Create tables BEFORE ingestion starts
        self._create_tables_locked()

        # Open tables
        self.papers = self.db.open_table(self.config.papers_table)
        self.chunks = self.db.open_table(self.config.chunks_table)

        # Validate schema
        self._validate_schema()

    # --------------------------------------------------------
    # Locked Schema Creation
    # --------------------------------------------------------

    def _create_tables_locked(self):
        """
        Create tables with locked schema BEFORE ingestion.
        """

        papers_schema = pa.schema([
            pa.field("paper_id", pa.string()),
            pa.field("title", pa.string()),
            pa.field("authors", pa.list_(pa.string())),
            pa.field("year", pa.int32()),
            pa.field("doi", pa.string()),
            pa.field("file_path", pa.string()),
            pa.field("file_hash", pa.string()),
            pa.field("ingested_at", pa.string()),
        ])

        # FIXED: correct vector() signature for your LanceDB version
        chunks_schema = pa.schema([
            pa.field("chunk_id", pa.string()),
            pa.field("paper_id", pa.string()),
            pa.field("chunk_index", pa.int32()),
            pa.field("section", pa.string()),
            pa.field("token_start", pa.int32()),
            pa.field("token_end", pa.int32()),
            pa.field("text", pa.string()),
            pa.field("embedding", vector(384, pa.float32())),  # <-- FIXED
        ])

        if self.config.papers_table not in self.db.table_names():
            print(">>> Creating papers table with locked schema")
            self.db.create_table(self.config.papers_table, schema=papers_schema)

        if self.config.chunks_table not in self.db.table_names():
            print(">>> Creating chunks table with locked schema")
            self.db.create_table(self.config.chunks_table, schema=chunks_schema)

    # --------------------------------------------------------
    # Schema Validation
    # --------------------------------------------------------

    def _validate_schema(self):
        schema = self.db.open_table(self.config.chunks_table).schema
        emb_field = schema.field("embedding")

        if emb_field is None:
            raise RuntimeError("ERROR: 'embedding' column missing from schema.")

        t = emb_field.type

        # Must be a fixed-size vector<float32>[384]
        if not hasattr(t, "list_size"):
            raise RuntimeError(
                f"ERROR: embedding column is {t}, expected fixed_size_list<float32>[384]."
            )

        if t.value_type != pa.float32():
            raise RuntimeError(
                f"ERROR: embedding column dtype is {t.value_type}, expected float32."
            )

        if t.list_size != 384:
            raise RuntimeError(
                f"ERROR: embedding dimension is {t.list_size}, expected 384."
            )

        print(">>> Schema validated: embedding is fixed_size_list<float32>[384]")

    # --------------------------------------------------------
    # Paper-level operations
    # --------------------------------------------------------

    def paper_exists(self, file_hash: str) -> bool:
        result = (
            self.papers.search()
            .where(f"file_hash == '{file_hash}'")
            .limit(1)
            .to_list()
        )
        return len(result) > 0

    def insert_paper(self, metadata: Dict[str, Any]) -> str:
        paper_id = metadata.get("file_hash")
        row = {
            "paper_id": paper_id,
            "title": metadata.get("title"),
            "authors": metadata.get("authors"),
            "year": metadata.get("year"),
            "doi": metadata.get("doi"),
            "file_path": metadata.get("file_path"),
            "file_hash": metadata.get("file_hash"),
            "ingested_at": metadata.get("ingested_at"),
        }
        self.papers.add([row])
        return paper_id

    # --------------------------------------------------------
    # Chunk-level operations
    # --------------------------------------------------------

    def insert_chunks(self, paper_id: str, chunks: List[Any], embeddings: List[List[float]]):
        rows = []

        for chunk, emb in zip(chunks, embeddings):
            emb32 = np.asarray(emb, dtype=np.float32)

            if emb32.dtype != np.float32:
                raise RuntimeError("Embedding conversion to float32 failed.")

            if emb32.shape[0] != 384:
                raise RuntimeError(
                    f"Embedding dimension mismatch: got {emb32.shape[0]}, expected 384."
                )

            rows.append(
                {
                    "chunk_id": f"{paper_id}_{chunk.chunk_index}",
                    "paper_id": paper_id,
                    "chunk_index": chunk.chunk_index,
                    "section": chunk.section,
                    "token_start": chunk.token_start,
                    "token_end": chunk.token_end,
                    "text": chunk.text,
                    "embedding": emb32,  # <-- store NumPy array, not list
                }
            )

        self.chunks.add(rows)

    # --------------------------------------------------------
    # Query operations
    # --------------------------------------------------------

    def search(self, query_vector: List[float], k: int = 5):
        q = np.asarray(query_vector, dtype=np.float32)

        if q.shape[0] != 384:
            raise RuntimeError(
                f"Query vector dimension mismatch: got {q.shape[0]}, expected 384."
            )

        return self.chunks.search(q).limit(k).to_list()

    def get_paper_by_doi(self, doi: str):
        return self.papers.search().where(f"doi == '{doi}'").to_list()

    def get_chunks_by_paper(self, paper_id: str):
        return self.chunks.search().where(f"paper_id == '{paper_id}'").to_list()

    def get_papers_by_year(self, year: int):
        return self.papers.search().where(f"year == {year}").to_list()
