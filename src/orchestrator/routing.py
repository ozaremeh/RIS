# src/orchestrator/routing.py
"""
Routing subsystem for the orchestrator.

Responsibilities:
- Build full orchestrator prompt
- Call the learned router model
- Parse router JSON safely
- Apply heuristic overrides
- Apply confidence thresholds
- Produce a structured RoutingPlan
- Emit router callback metadata
"""

import json
import re
import datetime
from dataclasses import dataclass
from typing import Dict, List, Optional

from orchestrator.learned_router import choose_model_learned
from config import ROUTER_MODEL
from orchestrator.prompt_builder import build_orchestrator_prompt

print(">>> USING UPDATED ROUTING.PY <<<")

# ---------------------------------------------------------------------
# Logging helper
# ---------------------------------------------------------------------

def log_event(event: str, data: Dict = None) -> None:
    timestamp = datetime.datetime.now().isoformat(timespec="seconds")
    print(f"[ROUTER {timestamp}] {event}")
    if data:
        for key, value in data.items():
            print(f"    {key}: {value}")


# ---------------------------------------------------------------------
# Routing plan structure
# ---------------------------------------------------------------------

@dataclass
class RoutingPlan:
    strategy: str                 # "single", "parallel", "sequential"
    models: List[str]             # model keys (not LM Studio names)
    metadata: Dict                # router metadata (intent, confidence, etc.)


# ---------------------------------------------------------------------
# Robust JSON parsing helper
# ---------------------------------------------------------------------

def _safe_json_parse(text: str) -> Dict:
    """
    Extract and parse the first valid JSON object from the router output.
    Handles:
    - leading/trailing junk
    - newlines before JSON
    - extra commentary
    - multi-line JSON
    - partial JSON fragments
    """
    if not isinstance(text, str):
        raise ValueError(f"Router output is not a string: {text!r}")

    raw = text.strip()
    print("RAW ROUTER OUTPUT:", repr(raw))

    # Try to find a full JSON object
    match = re.search(r"\{[\s\S]*\}", raw)
    if match:
        json_str = match.group(0)
        try:
            return json.loads(json_str)
        except Exception:
            pass

    # If the router returned something like:
    #   "intent": "reasoning_light",
    #   "confidence": 0.9
    # Wrap it in braces
    if '"intent"' in raw:
        try:
            wrapped = "{ " + raw + " }"
            return json.loads(wrapped)
        except Exception:
            pass

    raise ValueError(f"Could not extract JSON from router output: {raw!r}")


# ---------------------------------------------------------------------
# Intent → model key mapping
# ---------------------------------------------------------------------

INTENT_TO_MODEL = {
    "coding": "coder",
    "math": "math",
    "reasoning_light": "reasoner",   # Phi‑4
    "reasoning_deep": "writer",      # Qwen‑72B
    "writing": "writer",
    "retrieval": "writer",           # embedder handled separately
    "architecture": "architecture",
    "general": "reasoner",
}

CONFIDENCE_THRESHOLD = 0.55
FALLBACK_MODELS = ["reasoner"]


# ---------------------------------------------------------------------
# Heuristic overrides
# ---------------------------------------------------------------------

def _heuristic_intent(user_message: str) -> Optional[str]:
    text = user_message.lower()

        # Architecture / codebase introspection
    if any(k in text for k in [
        "your architecture", "system architecture", "module structure",
        "dependency graph", "codebase", "how are you built",
        "your modules", "your orchestrator", "your ingestion pipeline",
        "architecture of your system", "architecture engine"
    ]):
        return "architecture"

    # Coding
    if any(k in text for k in ["python", "code", "function", "class", "bug", "stack trace", "traceback"]):
        return "coding"

    # Math
    if any(k in text for k in [
        "integral", "differentiate", "derivative", "limit", "matrix",
        "eigen", "jacobian", "gradient", "ode", "pde", "proof", "theorem"
    ]):
        return "math"

    # Deep reasoning (literature synthesis, hypothesis generation)
    if any(k in text for k in [
        "hypothesis", "synthesize", "compare across", "literature",
        "what does the evidence", "new conclusions", "emergent",
        "across papers", "summarize findings", "interpret"
    ]):
        return "reasoning_deep"

    # Light reasoning
    if any(k in text for k in ["explain", "analyze", "why", "how", "derive", "calculate"]):
        return "reasoning_light"

    # Writing
    if any(k in text for k in ["write", "draft", "expand", "summarize", "polish"]):
        return "writing"

    return None


def _looks_like_rag_query(user_message: str) -> bool:
    """
    Heuristic to detect queries that should go through the RAG engine.
    """
    text = user_message.lower()
    keywords = [
        "paper", "papers", "literature", "study", "studies",
        "mechanism", "pathway", "findings", "evidence",
        "hypothesis", "hypotheses",
        "compare across", "summarize across",
        "in the papers", "in these papers", "in the literature",
    ]
    return any(k in text for k in keywords)


# ---------------------------------------------------------------------
# Intent → model key
# ---------------------------------------------------------------------

def _choose_model_from_intent(intent: str) -> str:
    return INTENT_TO_MODEL.get(intent, "reasoner")


def _fallback_model() -> str:
    return FALLBACK_MODELS[0]


# ---------------------------------------------------------------------
# Build prompt + routing plan
# ---------------------------------------------------------------------

def build_prompt_and_plan(
    user_message: str,
    retrieval_mode: str,
    router_callback=None,
) -> (str, RoutingPlan):

    # 1. Build enriched prompt
    full_user_prompt = build_orchestrator_prompt(
        user_message,
        retrieval_mode,
    )

    # 1.5. Heuristic RAG override
    if _looks_like_rag_query(user_message):
        plan = RoutingPlan(
            strategy="single",
            models=["rag_query"],
            metadata={
                "intent": "rag",
                "confidence": 1.0,
                "task_type": "literature_inference",
                "complexity": None,
                "router_model": "heuristic_rag",
            },
        )

        if router_callback:
            try:
                router_callback({
                    "strategy": plan.strategy,
                    "models": plan.models,
                    "metadata": plan.metadata,
                    "prompt": full_user_prompt,
                })
            except Exception as e:
                log_event("Router callback error (RAG)", {"error": str(e)})

        return full_user_prompt, plan

    # 2. Call learned router
    try:
        router_output = choose_model_learned(user_message)
        print(">>> RAW ROUTER OUTPUT FROM MODEL:", repr(router_output))
        router_json = _safe_json_parse(router_output)

        intent = router_json.get("intent", "general")
        confidence = float(router_json.get("confidence", 0.0))
        task_type = router_json.get("task_type", None)
        complexity = router_json.get("complexity", None)

        # 3. Heuristic override
        heuristic = _heuristic_intent(user_message)
        if heuristic is not None:
            if confidence < CONFIDENCE_THRESHOLD:
                intent = heuristic
            else:
                if heuristic != intent:
                    log_event("Routing disagreement (router vs heuristic)", {
                        "router_intent": intent,
                        "heuristic_intent": heuristic,
                        "confidence": confidence,
                    })

        # 4. Confidence fallback
        if confidence < CONFIDENCE_THRESHOLD and heuristic is None:
            log_event("Router low confidence, falling back to reasoner", {
                "intent": intent,
                "confidence": confidence,
            })
            intent = "general"

        # 5. Choose model key
        model_key = _choose_model_from_intent(intent)

        # 6. Build routing plan
        plan = RoutingPlan(
            strategy="single",
            models=[model_key],
            metadata={
                "intent": intent,
                "confidence": confidence,
                "task_type": task_type,
                "complexity": complexity,
                "router_model": ROUTER_MODEL,
            },
        )

        log_event("Model routing decision", {
            "router_model": ROUTER_MODEL,
            "intent": intent,
            "confidence": confidence,
            "task_type": task_type,
            "complexity": complexity,
            "chosen_model_key": model_key,
        })

    except Exception as e:
        fallback = _fallback_model()
        log_event("Router failure", {
            "error": str(e),
            "error_type": type(e).__name__,
            "fallback_model": fallback,
        })
        plan = RoutingPlan(
            strategy="single",
            models=[fallback],
            metadata={"error": str(e)},
        )

    # 7. Emit router callback metadata
    if router_callback:
        try:
            router_callback({
                "strategy": plan.strategy,
                "models": plan.models,
                "metadata": plan.metadata,
                "prompt": full_user_prompt,
            })
        except Exception as e:
            log_event("Router callback error", {"error": str(e)})

    return full_user_prompt, plan
