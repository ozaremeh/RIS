from pathlib import Path

from ingestion.dependency_graph import build_dependency_graph
from ingestion.call_graph import build_call_graph
from ingestion.module_metrics import build_module_metrics
from refactoring.refactor_engine import RefactoringEngine

ROOT = Path(__file__).parent

def load_architecture_graph():
    return build_dependency_graph(ROOT)

def load_call_graph():
    return build_call_graph(ROOT)

def load_module_metrics():
    return build_module_metrics(ROOT)

def load_refactoring_suggestions():
    deps = build_dependency_graph(ROOT)
    calls = build_call_graph(ROOT)
    metrics = build_module_metrics(ROOT)

    engine = RefactoringEngine(deps, calls, metrics)
    return engine.suggest_refactors()