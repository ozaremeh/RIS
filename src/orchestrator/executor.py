# src/orchestrator/executor.py

"""
Model execution layer for the orchestrator.

Responsibilities:
- Run single-model calls (override or router-selected)
- Run parallel multi-model executions via ParallelExecutor
- Merge results according to routing strategy
- Provide helpers for streaming model selection
- Provide a dedicated RAG model execution helper
"""

from typing import List, Dict, Optional
import asyncio

from api_client import call_model
from parallel_executor import ParallelExecutor, ModelTask
from model_registry import get_model
from orchestrator.logging import log_event
from orchestrator.lifecycle import handle_specialist_continuity
from orchestrator.history import get_history


# ---------------------------------------------------------------------
# Parallel executor instance
# ---------------------------------------------------------------------

_executor = ParallelExecutor()


# ---------------------------------------------------------------------
# Result merging
# ---------------------------------------------------------------------

def _merge_results(plan, results: List[Dict]) -> str:
    """
    Merge outputs from multiple models according to the routing strategy.
    For now:
      - single: return the only output
      - parallel: prefer 'reasoner' if present, else first non-error
      - sequential: return the last output (placeholder for RAG pipelines)
    """
    if not results:
        return "[Error] No results from models."

    if plan.strategy == "single":
        return results[0].get("output") or "[Error] Model returned no output."

    if plan.strategy == "parallel":
        # Prefer reasoner if present
        for r in results:
            if r.get("model") == "reasoner" and r.get("output"):
                return r["output"]
        # Otherwise first non-error
        for r in results:
            if r.get("output"):
                return r["output"]
        return "[Error] All parallel models failed."

    if plan.strategy == "sequential":
        # Placeholder: later this will handle embedder -> reasoner RAG
        last = results[-1]
        return last.get("output") or "[Error] Sequential pipeline produced no output."

    return "[Error] Unknown routing strategy."


# ---------------------------------------------------------------------
# Single-model execution
# ---------------------------------------------------------------------

def run_single_model(
    model_name: str,
    messages: List[Dict[str, str]],
    reason: Optional[str] = None,
) -> str:
    """
    Execute a single model (override or router-selected) non-streaming.
    """
    handle_specialist_continuity(model_name)

    log_event("Sending request to model", {
        "model": model_name,
        "history_length": len(get_history()),
        "message_count": len(messages),
        "reason": reason or "single-model",
    })

    try:
        reply = call_model(model_name, messages)
    except Exception as e:
        reply = f"[Error] Model call failed: {e}"
        log_event("Model call error", {"error": str(e)})

    log_event("Model reply received", {
        "reply_preview": reply[:200] + "..."
    })

    return reply


# ---------------------------------------------------------------------
# RAG model execution helper
# ---------------------------------------------------------------------

def run_rag_model(
    model_name: str,
    prompt: str,
) -> str:
    """
    Execute a reasoning model for RAG using a single user prompt.
    This bypasses conversation history and system prompts.
    """
    handle_specialist_continuity(model_name)

    log_event("Sending RAG request to model", {
        "model": model_name,
        "prompt_preview": prompt[:200] + "...",
    })

    try:
        reply = call_model(model_name, [{"role": "user", "content": prompt}])
    except Exception as e:
        reply = f"[Error] RAG model call failed: {e}"
        log_event("RAG model call error", {"error": str(e)})

    log_event("RAG model reply received", {
        "reply_preview": reply[:200] + "..."
    })

    return reply


# ---------------------------------------------------------------------
# Parallel multi-model execution
# ---------------------------------------------------------------------

def run_parallel_models(
    routing_plan,
    tasks: List[ModelTask],
) -> str:
    """
    Execute multiple models in parallel according to the routing plan.
    """
    log_event("Sending parallel request to models", {
        "strategy": routing_plan.strategy,
        "models": routing_plan.models,
    })

    try:
        results = asyncio.run(_executor.run(tasks))
        reply = _merge_results(routing_plan, results)
    except Exception as e:
        reply = f"[Error] Parallel model execution failed: {e}"
        log_event("Parallel execution error", {"error": str(e)})

    log_event("Model reply received", {
        "reply_preview": reply[:200] + "..."
    })

    return reply


# ---------------------------------------------------------------------
# Streaming model selection helper
# ---------------------------------------------------------------------

def select_streaming_model(
    routing_plan,
    override_model_name: Optional[str] = None,
):
    """
    Decide which underlying model to use for streaming.

    Returns:
      model_name: str
      reason: str
    """
    if override_model_name is not None:
        return override_model_name, "override"

    # Router-selected: use the first model key and resolve via model_registry
    model_key = routing_plan.models[0]
    model_info = get_model(model_key)
    model_name = model_info["model_name"]
    reason = f"router-first ({model_key})"
    return model_name, reason
