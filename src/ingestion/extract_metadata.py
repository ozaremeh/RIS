# src/ingestion/extract_metadata.py

import re
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from pypdf import PdfReader


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def sha256_file(path: str) -> str:
    """Compute SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_doi_from_text(text: str) -> Optional[str]:
    """
    Extract DOI using a robust regex.
    DOIs are extremely standardized, so this works well.
    """
    doi_pattern = r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+"
    match = re.search(doi_pattern, text)
    return match.group(0) if match else None


def normalize_authors(raw: Optional[str]) -> list:
    """
    Convert PDF metadata author string into a list.
    PDF metadata often uses commas or semicolons.
    """
    if not raw:
        return []
    # Split on commas or semicolons
    parts = re.split(r"[;,]", raw)
    return [p.strip() for p in parts if p.strip()]


def extract_year_from_pdf_metadata(meta: Dict[str, Any]) -> Optional[int]:
    """
    Try to extract a year from PDF metadata fields.
    """
    candidates = [
        meta.get("/CreationDate"),
        meta.get("/ModDate"),
        meta.get("/Producer"),
        meta.get("/Subject"),
    ]

    for c in candidates:
        if not c:
            continue
        # Look for a 4-digit year between 1900–2100
        m = re.search(r"(19|20)\d{2}", str(c))
        if m:
            return int(m.group(0))

    return None


# ------------------------------------------------------------
# Main extraction function
# ------------------------------------------------------------

def extract_metadata(path: str, text: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract metadata from a PDF or DOCX file.
    For now, v1 supports PDF metadata + DOI detection.
    DOCX support can be added later.
    """

    path_obj = Path(path)
    ext = path_obj.suffix.lower()

    metadata = {
        "title": None,
        "authors": [],
        "year": None,
        "doi": None,
        "file_path": str(path_obj.resolve()),
        "file_hash": sha256_file(path),
        "ingested_at": datetime.now().isoformat(),
    }

    # --------------------------------------------------------
    # PDF metadata extraction
    # --------------------------------------------------------
    if ext == ".pdf":
        try:
            reader = PdfReader(path)
            pdf_meta = reader.metadata or {}

            # Title
            metadata["title"] = pdf_meta.get("/Title")

            # Authors
            metadata["authors"] = normalize_authors(pdf_meta.get("/Author"))

            # Year
            metadata["year"] = extract_year_from_pdf_metadata(pdf_meta)

        except Exception as e:
            print(f"[extract_metadata] PDF metadata extraction failed: {e}")

    # --------------------------------------------------------
    # DOI detection (requires text)
    # --------------------------------------------------------
    if text:
        doi = extract_doi_from_text(text)
        if doi:
            metadata["doi"] = doi

    # --------------------------------------------------------
    # Fallbacks
    # --------------------------------------------------------

    # If no title, try filename heuristic
    if not metadata["title"]:
        metadata["title"] = path_obj.stem.replace("_", " ").replace("-", " ").strip()

    # If no year, try to infer from filename
    if not metadata["year"]:
        m = re.search(r"(19|20)\d{2}", path_obj.stem)
        if m:
            metadata["year"] = int(m.group(0))

    return metadata
