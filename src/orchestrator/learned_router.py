# src/learned_router.py

from api_client import call_model
from config import ROUTER_MODEL
from prompt_builder import ROUTING_PROMPT   # <-- IMPORT THE REAL ONE
import inspect

print(">>> USING learned_router FROM:", inspect.getfile(inspect.currentframe()))


def choose_model_learned(user_message: str) -> str:
    """
    Call the learned router model with a clean system prompt,
    log everything, and return the raw text (even if it's junk).
    """

    print("\n=== ENTERED choose_model_learned() ===")
    print(">>> ROUTER_MODEL =", ROUTER_MODEL)
    print(">>> USER MESSAGE =", repr(user_message))
    print(">>> ROUTING_PROMPT =", repr(ROUTING_PROMPT))  # debug

    # -----------------------------
    # System prompt for the router
    # -----------------------------
    system_prompt = """
You are a routing classifier for a multi-model AI system.

Classify the user's message into one of the following intents:
- coding
- math
- reasoning_light
- reasoning_deep
- writing
- retrieval
- architecture
- general


Respond ONLY with a JSON object in this format:

{
  "intent": "<coding | math | reasoning_light | reasoning_deep | writing | retrieval | general>",
  "confidence": <float between 0 and 1>,
  "task_type": "<optional string>",
  "complexity": "<optional string>"
}

Return ONLY valid JSON. No commentary.
"""

    # -----------------------------
    # Build the user prompt
    # -----------------------------
    user_prompt = ROUTING_PROMPT.format(message=user_message)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    print(">>> ROUTER MESSAGES =", messages)

    # -----------------------------
    # Call the model
    # -----------------------------
    try:
        raw_response = call_model(ROUTER_MODEL, messages)
        print(">>> RAW ROUTER OUTPUT (inside choose_model_learned) =", repr(raw_response))
        return raw_response

    except Exception as e:
        print(">>> ROUTER MODEL CALL FAILED:", type(e).__name__, str(e))
        return f"ERROR: {type(e).__name__}: {e}"
