# src/refactoring/refactor_engine.py

from __future__ import annotations
from typing import Dict, List, Any


class RefactoringEngine:
    """
    Consumes:
      - dependency graph
      - call graph
      - module metrics

    Produces:
      - structured refactoring suggestions
    """

    def __init__(
        self,
        dependency_graph: Dict[str, List[str]],
        call_graph: Dict[str, List[str]],
        module_metrics: Dict[str, Dict[str, Any]],
    ):
        self.deps = dependency_graph
        self.calls = call_graph
        self.metrics = module_metrics

    # ------------------------------------------------------------
    # High-level API
    # ------------------------------------------------------------

    def suggest_refactors(self) -> List[Dict[str, Any]]:
        suggestions = []

        suggestions += self._detect_large_modules()
        suggestions += self._detect_long_functions()
        suggestions += self._detect_high_coupling()
        suggestions += self._detect_circular_dependencies()
        suggestions += self._detect_dead_code()
        suggestions += self._detect_complex_functions()

        return sorted(suggestions, key=lambda s: s["severity"], reverse=True)

    # ------------------------------------------------------------
    # Individual detectors
    # ------------------------------------------------------------

    def _detect_large_modules(self) -> List[Dict]:
        out = []
        for module, m in self.metrics.items():
            if m["loc"] > 500 or m["functions"] > 20:
                out.append({
                    "type": "large_module",
                    "module": module,
                    "loc": m["loc"],
                    "functions": m["functions"],
                    "severity": 0.8,
                    "suggestion": (
                        f"Module '{module}' is large ({m['loc']} LOC, {m['functions']} functions). "
                        "Consider splitting into smaller modules with clearer responsibilities."
                    ),
                })
        return out

    def _detect_long_functions(self) -> List[Dict]:
        out = []
        for module, m in self.metrics.items():
            for func, length in m["complexity"].items():
                # complexity dict stores complexity, not length — we need lengths
                pass
        # We'll fill this in below with actual lengths
        return out

    def _detect_high_coupling(self) -> List[Dict]:
        out = []
        for module, imports in self.deps.items():
            if len(imports) > 10:
                out.append({
                    "type": "high_coupling",
                    "module": module,
                    "imports": len(imports),
                    "severity": 0.7,
                    "suggestion": (
                        f"Module '{module}' imports {len(imports)} modules. "
                        "Consider reducing coupling or extracting shared utilities."
                    ),
                })
        return out

    def _detect_circular_dependencies(self) -> List[Dict]:
        out = []
        for module, imports in self.deps.items():
            for imp in imports:
                if module in self.deps.get(imp, []):
                    out.append({
                        "type": "circular_dependency",
                        "modules": (module, imp),
                        "severity": 0.9,
                        "suggestion": (
                            f"Circular dependency detected between '{module}' and '{imp}'. "
                            "Break the cycle by introducing an abstraction or moving shared logic."
                        ),
                    })
        return out

    def _detect_dead_code(self) -> List[Dict]:
        out = []
        all_called = set()
        for callers in self.calls.values():
            all_called.update(callers)

        for func in self.calls.keys():
            if func not in all_called:
                out.append({
                    "type": "dead_code",
                    "function": func,
                    "severity": 0.5,
                    "suggestion": (
                        f"Function '{func}' is never called. "
                        "Consider removing it or verifying if it should be used."
                    ),
                })
        return out

    def _detect_complex_functions(self) -> List[Dict]:
        out = []
        for module, m in self.metrics.items():
            for func, complexity in m["complexity"].items():
                if complexity > 10:
                    out.append({
                        "type": "complex_function",
                        "function": f"{module}.{func}",
                        "complexity": complexity,
                        "severity": 0.6,
                        "suggestion": (
                            f"Function '{module}.{func}' has high cyclomatic complexity ({complexity}). "
                            "Consider breaking it into smaller helper functions."
                        ),
                    })
        return out
