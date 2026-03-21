# lifecycle.py
"""
Model lifecycle management for specialist models:
- tracking which specialist model is active
- unloading on topic shift
- lazy-loading new specialists
- timestamping last use (for future idle timeouts)
"""

import time
from typing import Optional

from api_client import load_model_if_needed, unload_model
from orchestrator.logging import log_event  # optional helper if you want clean logging


# ---------------------------------------------------------------------
# Specialist model registry
# ---------------------------------------------------------------------

SPECIALIST_MODELS = {
    "deepseek-coder-6.7b",
    "deepseek-math-7b",
    "qwen-72b-gguf",
}

# Tracks the currently active specialist model
last_specialist_model: Optional[str] = None

# Tracks when the specialist was last used (for future idle timeout logic)
last_specialist_use_time: float = 0.0


# ---------------------------------------------------------------------
# Core continuity logic
# ---------------------------------------------------------------------

def handle_specialist_continuity(chosen_model: str) -> None:
    """
    Handles:
      - unloading previous specialist model if topic changed
      - loading new specialist model if needed
      - updating continuity trackers

    This function is called by orchestrator.py *after* routing chooses a model.
    """
    global last_specialist_model, last_specialist_use_time

    # If the chosen model is NOT a specialist
    if chosen_model not in SPECIALIST_MODELS:
        if last_specialist_model:
            log_event("Unloading previous specialist (topic shift)", {
                "previous_model": last_specialist_model
            })
            try:
                unload_model(last_specialist_model)
            except Exception as e:
                log_event("Specialist unload failed", {"error": str(e)})

        last_specialist_model = None
        return

    # If switching between specialists
    if last_specialist_model and last_specialist_model != chosen_model:
        log_event("Switching specialists", {
            "from": last_specialist_model,
            "to": chosen_model
        })
        try:
            unload_model(last_specialist_model)
        except Exception as e:
            log_event("Specialist unload failed", {"error": str(e)})

    # Load the new specialist if needed
    try:
        load_model_if_needed(chosen_model)
    except Exception as e:
        log_event("Specialist lazy-load failed", {"model": chosen_model, "error": str(e)})

    # Update continuity tracker
    last_specialist_model = chosen_model
    last_specialist_use_time = time.time()
    log_event("Specialist continuity updated", {
        "active_model": last_specialist_model
    })
