# src/ingestion/module_metrics.py

from __future__ import annotations
import ast
from pathlib import Path
from typing import Dict, List, Set


class MetricsVisitor(ast.NodeVisitor):
    """
    Walks a module AST and extracts:
      - function definitions
      - class definitions
      - function lengths
      - simple cyclomatic complexity
    """

    def __init__(self):
        self.function_lengths: Dict[str, int] = {}
        self.function_complexity: Dict[str, int] = {}
        self.class_count = 0
        self.function_count = 0

        self._current_function: List[str] = []
        self._start_line: List[int] = []

    # -----------------------------
    # Function / method definitions
    # -----------------------------

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.function_count += 1
        fq_name = node.name

        self._current_function.append(fq_name)
        self._start_line.append(node.lineno)

        # Initialize complexity
        self.function_complexity[fq_name] = 1  # base complexity

        self.generic_visit(node)

        # Compute function length
        start = self._start_line.pop()
        end = getattr(node, "end_lineno", start)
        self.function_lengths[fq_name] = end - start + 1

        self._current_function.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.visit_FunctionDef(node)

    # -----------------------------
    # Class definitions
    # -----------------------------

    def visit_ClassDef(self, node: ast.ClassDef):
        self.class_count += 1
        self.generic_visit(node)

    # -----------------------------
    # Cyclomatic complexity
    # -----------------------------

    def _bump_complexity(self):
        if self._current_function:
            name = self._current_function[-1]
            self.function_complexity[name] += 1

    def visit_If(self, node: ast.If):
        self._bump_complexity()
        self.generic_visit(node)

    def visit_For(self, node: ast.For):
        self._bump_complexity()
        self.generic_visit(node)

    def visit_While(self, node: ast.While):
        self._bump_complexity()
        self.generic_visit(node)

    def visit_Try(self, node: ast.Try):
        self._bump_complexity()
        self.generic_visit(node)

    def visit_With(self, node: ast.With):
        self._bump_complexity()
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp):
        self._bump_complexity()
        self.generic_visit(node)


# ------------------------------------------------------------
# Build metrics for entire codebase
# ------------------------------------------------------------

def build_module_metrics(root: Path) -> Dict[str, Dict]:
    """
    Returns:
      {
        "module.name": {
            "loc": int,
            "functions": int,
            "classes": int,
            "avg_func_length": float,
            "max_func_length": int,
            "complexity": {func: score},
        },
        ...
      }
    """
    metrics: Dict[str, Dict] = {}

    for path in root.rglob("*.py"):
        if "venv" in str(path) or "site-packages" in str(path):
            continue

        module_name = _path_to_module(root, path)
        text = path.read_text()

        try:
            tree = ast.parse(text)
        except Exception:
            continue

        visitor = MetricsVisitor()
        visitor.visit(tree)

        loc = text.count("\n") + 1
        func_lengths = visitor.function_lengths.values()

        metrics[module_name] = {
            "loc": loc,
            "functions": visitor.function_count,
            "classes": visitor.class_count,
            "avg_func_length": sum(func_lengths) / len(func_lengths) if func_lengths else 0,
            "max_func_length": max(func_lengths) if func_lengths else 0,
            "complexity": visitor.function_complexity,
        }

    return metrics


def _path_to_module(root: Path, path: Path) -> str:
    rel = path.relative_to(root).with_suffix("")
    return ".".join(rel.parts)
