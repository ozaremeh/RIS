# src/orchestrator/orchestrator.py

from __future__ import annotations
from typing import List, Dict
import json

from .history import (
    get_history,
    append_user_message,
    append_assistant_message,
    reset_history,
)

from semantic_memory import retrieve_semantic_memory
from episodic_memory import retrieve_episodic_memory, store_episode
from .semantic_manager import extract_facts_from_user_message
from emotion_classifier import classify_emotion

from .learned_router import choose_model_learned
from model_registry import get_model_name
from api_client import call_model, stream_model


# ============================================================
# Routing configuration
# ============================================================

ROUTER_CONFIDENCE_THRESHOLD = 0.55

# 🔑 Intent → logical model key
INTENT_TO_MODEL_KEY = {
    "reasoning_deep": "writer",     # Qwen‑32B
    "reasoning_light": "reasoner",  # Phi‑4
    "general": "reasoner",
    "coding": "coder",
    "math": "math",
}


def _route_model(user_message: str) -> Dict[str, str]:
    """
    Call the learned router and map intent → logical model key.
    """
    raw = choose_model_learned(user_message)

    intent = "general"
    confidence = 0.0

    try:
        data = json.loads(raw)
        intent = data.get("intent", "general")
        confidence = float(data.get("confidence", 0.0))
    except Exception:
        pass

    if confidence < ROUTER_CONFIDENCE_THRESHOLD:
        intent = "general"

    model_key = INTENT_TO_MODEL_KEY.get(intent, "reasoner")

    return {
        "intent": intent,
        "confidence": confidence,
        "chosen_model": model_key,
    }


# ============================================================
# Persona prompts
# ============================================================

# Ultra‑minimal Phi‑4 prompt
PHI4_PERSONA = "Answer the user's question directly and clearly."

# Rich persona for large models (Qwen, etc.)
BASE_PERSONA = (
    "You are RIS, a research intelligence system with a warm, grounded, conversational voice.\n"
    "You speak like a thoughtful, emotionally intelligent collaborator.\n\n"
    "Tone:\n"
    "- Natural, calm, and steady.\n"
    "- Warm without being bubbly.\n"
    "- Direct, but gentle.\n\n"
    "Memory rules:\n"
    "- Use SEMANTIC MEMORY for stable facts and preferences.\n"
    "- Use EPISODIC MEMORY only when clearly relevant.\n"
    "- Ignore unrelated memory.\n"
)


# ============================================================
# Tone modifier (non‑Phi‑4 only)
# ============================================================

def _build_tone_modifier(user_message: str) -> str:
    emotion = classify_emotion(user_message)

    if emotion == "frustration":
        return "Respond with calm clarity and grounded empathy.\n"
    if emotion == "fatigue":
        return "Keep your tone soft and steady.\n"
    if emotion == "sadness":
        return "Be warm and steady without sentimentality.\n"
    if emotion == "anxiety":
        return "Be calm, structured, and reassuring.\n"
    return ""


# ============================================================
# Model behavior gates
# ============================================================

def _is_phi4(model_name: str) -> bool:
    return model_name.lower().startswith("phi-4")


# ============================================================
# Memory injection
# ============================================================

def _inject_memory_context(messages, semantic_hits, episodic_hits):
    if semantic_hits:
        messages.append({
            "role": "system",
            "content": "Relevant semantic memory:\n" + "\n".join(f"- {h}" for h in semantic_hits)
        })

    if episodic_hits:
        messages.append({
            "role": "system",
            "content": "Relevant past interactions:\n" + "\n".join(
                f"- [{e.get('timestamp','')}] {e.get('role','')}: {e.get('content','')}"
                for e in episodic_hits
            )
        })


# ============================================================
# Message builder
# ============================================================

def _build_messages(model_name: str, user_message: str) -> List[Dict[str, str]]:
    """
    Build OpenAI‑style messages.

    Phi‑4:
      - no history
      - no semantic/episodic injection
      - clean 2‑message context
    """
    if _is_phi4(model_name):
        return [
            {"role": "system", "content": PHI4_PERSONA},
            {"role": "user", "content": user_message},
        ]

    # Non‑Phi‑4: full RIS behavior
    semantic_hits = retrieve_semantic_memory(user_message)
    episodic_hits = retrieve_episodic_memory(user_message)

    filtered_history = [m for m in get_history() if m["role"] != "system"]

    system_prompt = BASE_PERSONA + _build_tone_modifier(user_message)

    messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
    _inject_memory_context(messages, semantic_hits, episodic_hits)
    messages.extend(filtered_history)
    messages.append({"role": "user", "content": user_message})

    return messages


# ============================================================
# Streaming entry point
# ============================================================

def send_message_streaming(
    user_message: str,
    override_model: str = None,
    router_callback=None,
) -> str:

    append_user_message(user_message)
    store_episode("user", user_message)

    if override_model:
        model_key = override_model
        confidence = 1.0
        intent = "override"
    else:
        routing = _route_model(user_message)
        model_key = routing["chosen_model"]
        confidence = routing["confidence"]
        intent = routing["intent"]

    model_name = get_model_name(model_key)
    messages = _build_messages(model_name, user_message)

    if router_callback:
        router_callback({
            "intent": intent,
            "confidence": confidence,
            "model_key": model_key,
            "model_name": model_name,
        })

    reply_chunks: List[str] = []
    for chunk in stream_model(model_name, messages):
        reply_chunks.append(chunk)

    reply = "".join(reply_chunks)

    append_assistant_message(reply)
    store_episode("assistant", reply)
    extract_facts_from_user_message(user_message, reply)

    return reply


# ============================================================
# Non‑streaming entry point
# ============================================================

def send_message(
    user_message: str,
    override_model: str = None,
    router_callback=None,
) -> str:

    append_user_message(user_message)
    store_episode("user", user_message)

    if override_model:
        model_key = override_model
        confidence = 1.0
        intent = "override"
    else:
        routing = _route_model(user_message)
        model_key = routing["chosen_model"]
        confidence = routing["confidence"]
        intent = routing["intent"]

    model_name = get_model_name(model_key)
    messages = _build_messages(model_name, user_message)

    if router_callback:
        router_callback({
            "intent": intent,
            "confidence": confidence,
            "model_key": model_key,
            "model_name": model_name,
        })

    reply = call_model(model_name, messages)

    append_assistant_message(reply)
    store_episode("assistant", reply)
    extract_facts_from_user_message(user_message, reply)

    return reply
