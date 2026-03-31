# src/ingestion/code_chunker.py

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
import ast
import textwrap


@dataclass
class CodeChunk:
    text: str
    chunk_index: int
    block_type: str          # "class", "function", "method", "import", "module"
    name: Optional[str]
    start_line: int
    end_line: int
    metadata: dict


# ------------------------------------------------------------
# AST utilities
# ------------------------------------------------------------

def get_source_segment(source: str, node: ast.AST) -> str:
    """Extract exact source code for an AST node."""
    lines = source.splitlines()
    start = node.lineno - 1
    end = node.end_lineno
    return "\n".join(lines[start:end])


def extract_imports(tree: ast.AST, source: str) -> List[CodeChunk]:
    chunks = []
    idx = 0

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            text = get_source_segment(source, node)
            chunks.append(
                CodeChunk(
                    text=text,
                    chunk_index=idx,
                    block_type="import",
                    name=None,
                    start_line=node.lineno,
                    end_line=node.end_lineno,
                    metadata={},
                )
            )
            idx += 1

    return chunks


def extract_classes(tree: ast.AST, source: str) -> List[CodeChunk]:
    chunks = []
    idx = 0

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            text = get_source_segment(source, node)
            chunks.append(
                CodeChunk(
                    text=text,
                    chunk_index=idx,
                    block_type="class",
                    name=node.name,
                    start_line=node.lineno,
                    end_line=node.end_lineno,
                    metadata={},
                )
            )
            idx += 1

    return chunks


def extract_functions(tree: ast.AST, source: str) -> List[CodeChunk]:
    chunks = []
    idx = 0

    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            text = get_source_segment(source, node)
            chunks.append(
                CodeChunk(
                    text=text,
                    chunk_index=idx,
                    block_type="function",
                    name=node.name,
                    start_line=node.lineno,
                    end_line=node.end_lineno,
                    metadata={},
                )
            )
            idx += 1

    return chunks


def extract_methods(tree: ast.AST, source: str) -> List[CodeChunk]:
    chunks = []
    idx = 0

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, ast.FunctionDef):
                    text = get_source_segment(source, sub)
                    chunks.append(
                        CodeChunk(
                            text=text,
                            chunk_index=idx,
                            block_type="method",
                            name=f"{node.name}.{sub.name}",
                            start_line=sub.lineno,
                            end_line=sub.end_lineno,
                            metadata={"class": node.name},
                        )
                    )
                    idx += 1

    return chunks


# ------------------------------------------------------------
# Main AST-aware chunker
# ------------------------------------------------------------

def chunk_code_ast(text: str, module: str, max_tokens: int = 512, overlap: int = 64) -> List[CodeChunk]:
    """
    AST-aware code chunker:
    - Extracts imports, classes, functions, methods
    - Extracts remaining top-level statements as module chunks
    - Falls back to token-window chunking for long blocks
    """

    try:
        tree = ast.parse(text)
    except SyntaxError:
        # Fallback: treat as plain text
        return [
            CodeChunk(
                text=text,
                chunk_index=0,
                block_type="module",
                name=module,
                start_line=1,
                end_line=len(text.splitlines()),
                metadata={"module": module},
            )
        ]

    chunks: List[CodeChunk] = []
    idx = 0

    # Extract structured blocks
    imports = extract_imports(tree, text)
    classes = extract_classes(tree, text)
    functions = extract_functions(tree, text)
    methods = extract_methods(tree, text)

    structured = imports + classes + functions + methods

    # Assign chunk indices
    for c in structured:
        c.chunk_index = idx
        c.metadata["module"] = module
        idx += 1
        chunks.append(c)

    # ------------------------------------------------------------
    # Extract remaining top-level statements as module chunks
    # ------------------------------------------------------------

    used_lines = set()
    for c in structured:
        used_lines.update(range(c.start_line, c.end_line + 1))

    lines = text.splitlines()
    current_block = []
    start_line = None

    for i, line in enumerate(lines, start=1):
        if i in used_lines:
            if current_block:
                block_text = "\n".join(current_block)
                chunks.append(
                    CodeChunk(
                        text=block_text,
                        chunk_index=idx,
                        block_type="module",
                        name=module,
                        start_line=start_line,
                        end_line=i - 1,
                        metadata={"module": module},
                    )
                )
                idx += 1
                current_block = []
                start_line = None
            continue

        if start_line is None:
            start_line = i
        current_block.append(line)

    if current_block:
        block_text = "\n".join(current_block)
        chunks.append(
            CodeChunk(
                text=block_text,
                chunk_index=idx,
                block_type="module",
                name=module,
                start_line=start_line,
                end_line=len(lines),
                metadata={"module": module},
            )
        )

    # ------------------------------------------------------------
    # Token-window fallback for long chunks
    # ------------------------------------------------------------

    final_chunks: List[CodeChunk] = []
    new_idx = 0

    for c in chunks:
        tokens = c.text.split()
        if len(tokens) > max_tokens:
            start = 0
            while start < len(tokens):
                end = min(start + max_tokens, len(tokens))
                window = " ".join(tokens[start:end])

                final_chunks.append(
                    CodeChunk(
                        text=window,
                        chunk_index=new_idx,
                        block_type=c.block_type,
                        name=c.name,
                        start_line=c.start_line,
                        end_line=c.end_line,
                        metadata=c.metadata,
                    )
                )
                new_idx += 1
                start = max(0, end - overlap)
        else:
            c.chunk_index = new_idx
            final_chunks.append(c)
            new_idx += 1

    return final_chunks
