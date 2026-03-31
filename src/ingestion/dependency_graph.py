# src/ingestion/dependency_graph.py

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set
import ast


@dataclass(frozen=True)
class ModuleDependencies:
    module: str
    imports: frozenset[str]
    calls: frozenset[str]
    classes: frozenset[str]
    functions: frozenset[str]

    def __len__(self):
        return (
            len(self.imports)
            + len(self.calls)
            + len(self.classes)
            + len(self.functions)
        )

    def __iter__(self):
        yield from {
            "module": self.module,
            "imports": self.imports,
            "calls": self.calls,
            "classes": self.classes,
            "functions": self.functions,
        }.items()

    def __repr__(self):
        return (
            f"ModuleDependencies("
            f"module={self.module!r}, "
            f"imports={len(self.imports)}, "
            f"calls={len(self.calls)}, "
            f"classes={len(self.classes)}, "
            f"functions={len(self.functions)})"
        )


# ------------------------------------------------------------
# Utility: extract module name from path
# ------------------------------------------------------------

def path_to_module(path: Path, root: Path) -> str:
    rel = path.relative_to(root)
    return rel.with_suffix("").as_posix().replace("/", ".")


# ------------------------------------------------------------
# Extract imports from AST
# ------------------------------------------------------------

def extract_imports(tree: ast.AST) -> Set[str]:
    imports = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])

    return imports


# ------------------------------------------------------------
# Extract class and function names
# ------------------------------------------------------------

def extract_classes_and_functions(tree: ast.AST) -> (Set[str], Set[str]):
    classes = set()
    functions = set()

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            classes.add(node.name)
        elif isinstance(node, ast.FunctionDef):
            functions.add(node.name)

    return classes, functions


# ------------------------------------------------------------
# Extract function/method calls
# ------------------------------------------------------------

def extract_calls(tree: ast.AST) -> Set[str]:
    calls = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
            elif isinstance(node.func, ast.Name):
                calls.add(node.func.id)

    return calls


# ------------------------------------------------------------
# Main dependency graph builder
# ------------------------------------------------------------

def build_dependency_graph(root: Path) -> Dict[str, ModuleDependencies]:
    """
    Build a dependency graph for all Python modules under `root`.
    Returns a dict: module_name -> ModuleDependencies
    """

    graph: Dict[str, ModuleDependencies] = {}

    for path in root.rglob("*.py"):
        try:
            source = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue

        module = path_to_module(path, root)

        imports = extract_imports(tree)
        classes, functions = extract_classes_and_functions(tree)
        calls = extract_calls(tree)

        graph[module] = ModuleDependencies(
            module=module,
            imports=frozenset(imports),
            calls=frozenset(calls),
            classes=frozenset(classes),
            functions=frozenset(functions),
     )


    return graph
