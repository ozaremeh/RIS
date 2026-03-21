# src/model_router.py

from __future__ import annotations
import json
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from model_registry import get_model
from parallel_executor import ModelTask
from api_client import call_model


# ------------------------------------------------------------
# Routing Plan
# ------------------------------------------------------------

@dataclass
class RoutingPlan:
    strategy: str               # "single", "parallel", "sequential"
    models: List[str]           # logical model keys from registry
    prompt: str
    metadata: Dict[str, Any]


# ------------------------------------------------------------
# Learned Router (Phi-3 Mini)
# ------------------------------------------------------------

ROUTER_MODEL_KEY = "router"


def _safe_parse_router_json(raw: str) -> Optional[Dict[str, Any]]:
    if not raw or not isinstance(raw, str):
        return None

    text = raw.strip()
    start = text.find("{")
    if start == -1:
        return None
    text = text[start:]

    end = text.rfind("}")
    if end == -1:
        return None
    text = text[: end + 1]

    try:
        return json.loads(text)
    except Exception:
        return None


def classify_intent_with_phi3(user_message: str) -> Optional[Dict[str, Any]]:
    router_info = get_model(ROUTER_MODEL_KEY)

    router_prompt = f"""
You are a routing classifier for a multi-model AI system.

Classify the user's message into one of the following intents:
- coding
- math
- reasoning_light
- reasoning_deep
- writing
- retrieval
- general

Respond ONLY with a JSON object in this format:

{{
  "intent": "<coding | math | reasoning_light | reasoning_deep | writing | retrieval | general>",
  "confidence": <float between 0 and 1>
}}

User message:
{user_message}
"""

    messages = [{"role": "user", "content": router_prompt}]

    try:
        raw = call_model(router_info["model_name"], messages)
    except Exception:
        return None

    data = _safe_parse_router_json(raw)
    if not data:
        return None

    try:
        confidence = float(data.get("confidence", 0.0))
    except Exception:
        confidence = 0.0

    return {
        "intent": data.get("intent", "general"),
        "confidence": confidence,
        "raw_router_output": raw,
    }


# ------------------------------------------------------------
# Rule-based fallback router
# ------------------------------------------------------------

def rule_based_intent(user_message: str) -> str:
    lower = user_message.lower()

    # Coding
    if any(k in lower for k in ["python", "code", "function", "bug", "error", "stack trace"]):
        return "coding"

    # Math
    if any(k in lower for k in [
        "solve", "integral", "derivative", "differentiate", "limit",
        "matrix", "eigen", "eigenvalue", "eigenvector",
        "gradient", "jacobian", "hessian",
        "ode", "pde", "laplace", "fourier",
        "theorem", "lemma", "proof", "compute", "evaluate"
    ]):
        return "math"

    # Deep reasoning (literature synthesis, hypothesis generation)
    if any(k in lower for k in [
        "hypothesis", "synthesize", "compare across", "literature",
        "what does the evidence", "new conclusions", "emergent",
        "across papers", "summarize findings", "interpret"
    ]):
        return "reasoning_deep"

    # Light reasoning
    if any(k in lower for k in ["prove", "derive", "calculate", "explain", "why", "how"]):
        return "reasoning_light"

    # Writing
    if any(k in lower for k in ["write", "draft", "expand", "summarize"]):
        return "writing"

    # Retrieval
    if any(k in lower for k in ["paper", "study", "literature", "citation", "epha2"]):
        return "retrieval"

    return "general"


# ------------------------------------------------------------
# Router
# ------------------------------------------------------------

class Router:
    def __init__(self, confidence_threshold: float = 0.55):
        self.confidence_threshold = confidence_threshold

    def route(self, prompt: str, override: Optional[str] = None) -> RoutingPlan:

        if override:
            return RoutingPlan(
                strategy="single",
                models=[override],
                prompt=prompt,
                metadata={"reason": "manual override"},
            )

        learned = classify_intent_with_phi3(prompt)

        if learned and learned["confidence"] >= self.confidence_threshold:
            return self._intent_to_plan(learned["intent"], prompt, learned)

        intent = rule_based_intent(prompt)
        return self._intent_to_plan(intent, prompt, {"reason": "rule-based fallback"})

    def _intent_to_plan(self, intent: str, prompt: str, metadata: Dict[str, Any]) -> RoutingPlan:

        if intent == "coding":
            return RoutingPlan(
                strategy="parallel",
                models=["coder", "reasoner"],  # coder + Phi-4
                prompt=prompt,
                metadata={"intent": intent, **metadata},
            )

        if intent == "math":
            return RoutingPlan(
                strategy="single",
                models=["math"],
                prompt=prompt,
                metadata={"intent": intent, **metadata},
            )

        if intent == "reasoning_light":
            return RoutingPlan(
                strategy="single",
                models=["reasoner"],  # Phi-4
                prompt=prompt,
                metadata={"intent": intent, **metadata},
            )

        if intent == "reasoning_deep":
            return RoutingPlan(
                strategy="single",
                models=["writer"],  # Qwen2.5 72B
                prompt=prompt,
                metadata={"intent": intent, **metadata},
            )

        if intent == "writing":
            return RoutingPlan(
                strategy="parallel",
                models=["writer", "reasoner"],  # Qwen72B + Phi-4
                prompt=prompt,
                metadata={"intent": intent, **metadata},
            )

        if intent == "retrieval":
            return RoutingPlan(
                strategy="sequential",
                models=["embedder", "writer"],  # embedder → Qwen72B
                prompt=prompt,
                metadata={"intent": intent, **metadata},
            )

        return RoutingPlan(
            strategy="single",
            models=["reasoner"],  # safe default: Phi-4
            prompt=prompt,
            metadata={"intent": "general", **metadata},
        )

    def to_tasks(self, plan: RoutingPlan) -> List[ModelTask]:
        tasks: List[ModelTask] = []
        for model_key in plan.models:
            tasks.append(
                ModelTask(
                    model_key=model_key,
                    prompt=plan.prompt,
                    metadata=plan.metadata,
                )
            )
        return tasks
