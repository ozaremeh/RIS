# src/orchestrator/orchestrator.py

from typing import List, Dict, Optional

from api_client import stream_model
from memory import log_message

from orchestrator.memory_pipeline import process_memory_pipeline
from orchestrator.history import (
    get_history,
    append_user_message,
    append_assistant_message,
    reset_history as reset_history_internal,
)
from orchestrator.logging import log_event
from orchestrator.routing import build_prompt_and_plan
from orchestrator.executor import run_single_model, select_streaming_model
from orchestrator.semantic_manager import extract_facts_from_user_message, set_pending_facts
from orchestrator.lifecycle import handle_specialist_continuity

from reasoning.rag_engine import RAGEngine
from ingestion.vector_store import VectorStore
from ingestion.embedder import Embedder
from model_registry import get_model


# ---------------------------------------------------------------------
# Retrieval mode (mutable container)
# ---------------------------------------------------------------------

RETRIEVAL_MODE = {"mode": "conservative"}


# ---------------------------------------------------------------------
# Simple LLM wrapper for RAGEngine
# ---------------------------------------------------------------------

class LLMWrapper:
    """
    Wraps a callable(prompt: str) -> str into an object
    exposing a .generate(prompt: str) -> str API.
    """

    def __init__(self, fn):
        self.fn = fn

    def generate(self, prompt: str) -> str:
        return self.fn(prompt)


# ---------------------------------------------------------------------
# RAG engine initialization
# ---------------------------------------------------------------------

VECTOR_STORE = VectorStore()
EMBEDDER = Embedder()

# Reasoning model for RAG (must be defined in model_registry under key "reasoning")
REASONING_MODEL_NAME = get_model("reasoning")["model_name"]

RAG_ENGINE = RAGEngine(
    vector_store=VECTOR_STORE,
    embedder=EMBEDDER,
    llm=LLMWrapper(
        lambda prompt: run_single_model(
            REASONING_MODEL_NAME,
            [{"role": "user", "content": prompt}],
            reason="rag",
        )
    ),
)


# ---------------------------------------------------------------------
# Main orchestrator entry point (non-streaming)
# ---------------------------------------------------------------------

def send_message(
    user_message: str,
    override_model: Optional[str] = None,
    bypass_memory: bool = False,
    router_callback=None,
) -> str:
    log_event("Received user message", {"message": user_message})

    # Manual unload command
    if user_message.strip().lower() == "/unload_writing":
        from ..api_client import unload_model
        try:
            unload_model("qwen-72b-gguf")
            reply = "Unloaded the writing model from memory."
        except Exception as e:
            reply = f"[Error] Failed to unload writing model: {e}"
        log_event("Manual unload command", {"model": "qwen-72b-gguf"})
        return reply

    # 1. Memory pipeline (semantic confirmation, mode commands, NL commands)
    if not bypass_memory:
        retrieval_mode_ref = {"mode": RETRIEVAL_MODE["mode"]}
        memory_result = process_memory_pipeline(user_message, retrieval_mode_ref)
        RETRIEVAL_MODE["mode"] = retrieval_mode_ref["mode"]

        if memory_result.intercepted:
            return memory_result.reply

    # 2. Build prompt + routing plan
    full_user_prompt, routing_plan = build_prompt_and_plan(
        user_message,
        RETRIEVAL_MODE["mode"],
        router_callback=router_callback,
    )

    # --- RAG route handler (non-streaming) ---
    if routing_plan.models and routing_plan.models[0] == "rag_query":
        result = RAG_ENGINE.query(user_message)
        reply = (
            result["answer"]
            + "\n\nSources: "
            + ", ".join(result["sources"])
        )

        # Update conversation history
        append_user_message(user_message)
        append_assistant_message(reply)

        # Log to episodic long-term memory
        log_message("user", user_message)
        log_message("assistant", reply)

        return reply

    # 3. Build messages list (system + history + user)
    messages: List[Dict[str, str]] = []

    messages.append({
        "role": "system",
        "content": (
            "You are a helpful, precise research assistant. "
            "Use SEMANTIC MEMORY for stable facts and preferences. "
            "Use EPISODIC MEMORY only when clearly relevant. "
            "If memory is unrelated, ignore it."
        )
    })

    messages.extend(get_history())
    messages.append({"role": "user", "content": full_user_prompt})

    # 4. Choose model and execute (single-model for now)
    if override_model is not None:
        model_name = override_model
        reason = "override"
    else:
        model_key = routing_plan.models[0]
        model_info = get_model(model_key)
        model_name = model_info["model_name"]
        reason = f"router ({model_key})"

    reply = run_single_model(model_name, messages, reason=reason)

    # 5. Semantic memory extraction (post-reply, same turn)
    extraction = extract_facts_from_user_message(user_message)

    if extraction.has_facts and extraction.confirmation_prompt:
        set_pending_facts(extraction.facts)
        reply = reply + "\n\n" + extraction.confirmation_prompt

    # 6. Update conversation history
    append_user_message(full_user_prompt)
    append_assistant_message(reply)

    # 7. Log to episodic long-term memory
    log_message("user", user_message)
    log_message("assistant", reply)

    return reply


# ---------------------------------------------------------------------
# Streaming orchestrator entry point
# ---------------------------------------------------------------------

def send_message_streaming(
    user_message: str,
    override_model: Optional[str] = None,
    bypass_memory: bool = False,
    router_callback=None,
):
    log_event("Received user message (streaming)", {"message": user_message})

    # Manual unload command
    if user_message.strip().lower() == "/unload_writing":
        from ..api_client import unload_model
        try:
            unload_model("qwen-72b-gguf")
            reply = "Unloaded the writing model from memory."
        except Exception as e:
            reply = f"[Error] Failed to unload writing model: {e}"
        log_event("Manual unload command (streaming)", {"model": "qwen-72b-gguf"})
        yield reply
        return

    # 1. Memory pipeline
    if not bypass_memory:
        retrieval_mode_ref = {"mode": RETRIEVAL_MODE["mode"]}
        memory_result = process_memory_pipeline(user_message, retrieval_mode_ref)
        RETRIEVAL_MODE["mode"] = retrieval_mode_ref["mode"]

        if memory_result.intercepted:
            yield memory_result.reply
            return

    # 2. Build prompt + routing plan
    full_user_prompt, routing_plan = build_prompt_and_plan(
        user_message,
        RETRIEVAL_MODE["mode"],
        router_callback=router_callback,
    )

    # --- RAG route handler (streaming, but using non-streaming RAG) ---
    if routing_plan.models and routing_plan.models[0] == "rag_query":
        result = RAG_ENGINE.query(user_message)
        reply = (
            result["answer"]
            + "\n\nSources: "
            + ", ".join(result["sources"])
        )

        # Update conversation history
        append_user_message(user_message)
        append_assistant_message(reply)

        # Log to episodic long-term memory
        log_message("user", user_message)
        log_message("assistant", reply)

        yield reply
        return

    # 3. Build messages list
    messages: List[Dict[str, str]] = []

    messages.append({
        "role": "system",
        "content": (
            "You are a helpful, precise research assistant. "
            "Use SEMANTIC MEMORY for stable facts and preferences. "
            "Use EPISODIC MEMORY only when clearly relevant. "
            "If memory is unrelated, ignore it."
        )
    })

    messages.extend(get_history())
    messages.append({"role": "user", "content": full_user_prompt})

    # 4. Select streaming model
    model_name, reason = select_streaming_model(
        routing_plan,
        override_model_name=override_model,
    )

    handle_specialist_continuity(model_name)

    log_event("Sending request to model (streaming)", {
        "model": model_name,
        "history_length": len(get_history()),
        "message_count": len(messages),
        "reason": reason,
    })

    full_reply = ""

    try:
        for token in stream_model(model_name, messages):
            full_reply += token
            yield token
    except Exception as e:
        err = f"[Error] Model streaming failed: {e}"
        log_event("Model streaming error", {"error": str(e)})
        log_message("user", user_message)
        log_message("assistant", err)
        yield err
        return

    log_event("Model streaming reply completed", {
        "reply_preview": full_reply[:200] + "..."
    })

    # 5. Semantic memory extraction (post-reply)
    extraction = extract_facts_from_user_message(user_message)

    if extraction.has_facts and extraction.confirmation_prompt:
        set_pending_facts(extraction.facts)
        question = "\n" + extraction.confirmation_prompt
        yield question
        full_reply = full_reply + question

    # 6. Update conversation history
    append_user_message(full_user_prompt)
    append_assistant_message(full_reply)

    # 7. Log to episodic long-term memory
    log_message("user", user_message)
    log_message("assistant", full_reply)


# ---------------------------------------------------------------------
# Reset conversation history
# ---------------------------------------------------------------------

def reset_history() -> None:
    reset_history_internal()
