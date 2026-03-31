# src/ingestion/call_graph.py

from __future__ import annotations
import ast
from pathlib import Path
from typing import Dict, List, Set, Tuple


class CallGraphVisitor(ast.NodeVisitor):
    """
    Walks a module AST and extracts:
      - function definitions
      - method definitions
      - calls inside each function/method
    """

    def __init__(self, module_name: str):
        self.module_name = module_name
        self.current_function: List[str] = []
        self.calls: Dict[str, Set[str]] = {}
        self.defined_functions: Set[str] = set()

    # -----------------------------
    # Function / method definitions
    # -----------------------------

    def visit_FunctionDef(self, node: ast.FunctionDef):
        fq_name = f"{self.module_name}.{node.name}"
        self.defined_functions.add(fq_name)

        self.current_function.append(fq_name)
        self.calls.setdefault(fq_name, set())

        self.generic_visit(node)
        self.current_function.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.visit_FunctionDef(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        class_name = f"{self.module_name}.{node.name}"
        self.generic_visit(node)

    # -----------------------------
    # Call extraction
    # -----------------------------

    def visit_Call(self, node: ast.Call):
        if not self.current_function:
            return

        caller = self.current_function[-1]

        # Extract callee name
        callee = self._extract_callee_name(node.func)
        if callee:
            self.calls[caller].add(callee)

        self.generic_visit(node)

    def _extract_callee_name(self, node) -> str | None:
        # direct call: foo()
        if isinstance(node, ast.Name):
            return node.id

        # attribute call: module.func or obj.method
        if isinstance(node, ast.Attribute):
            parts = []
            while isinstance(node, ast.Attribute):
                parts.append(node.attr)
                node = node.value
            if isinstance(node, ast.Name):
                parts.append(node.id)
            return ".".join(reversed(parts))

        return None


# ------------------------------------------------------------
# Build call graph for entire codebase
# ------------------------------------------------------------

def build_call_graph(root: Path) -> Dict[str, Set[str]]:
    """
    Returns:
      {
        "module.func": {"callee1", "callee2", ...},
        ...
      }
    """
    call_graph: Dict[str, Set[str]] = {}

    for path in root.rglob("*.py"):
        if "venv" in str(path) or "site-packages" in str(path):
            continue

        module_name = _path_to_module(root, path)

        try:
            tree = ast.parse(path.read_text())
        except Exception:
            continue

        visitor = CallGraphVisitor(module_name)
        visitor.visit(tree)

        for func, callees in visitor.calls.items():
            call_graph.setdefault(func, set()).update(callees)

    return call_graph


def _path_to_module(root: Path, path: Path) -> str:
    rel = path.relative_to(root).with_suffix("")
    return ".".join(rel.parts)
