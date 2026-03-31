# src/model_executor.py

"""
Model executor for RIS.
Dispatches calls to:
- LLMs (via api_client)
- Embedding models
- Internal models (architecture retriever)
- Stubbed fallback executor
"""

from __future__ import annotations
from typing import Any, Dict

from model_registry import get_model
from api_client import call_model
from retrieval_architecture import architecture_query


def run_model(model_key: str, prompt: str) -> Any:
    """
    Main model execution entry point.
    Dispatches based on model type:
      - llm → call_model()
      - embedding → call_model()
      - internal → custom Python handler
      - router → call_model()
      - fallback → stubbed executor
    """

    model_info = get_model(model_key)
    model_type = model_info.get("type")

    # ------------------------------------------------------------
    # Internal architecture model
    # ------------------------------------------------------------
    if model_type == "internal" and model_key == "architecture":
        # Directly run architecture graph query
        return architecture_query(prompt)

    # ------------------------------------------------------------
    # LLMs, embedding models, router models
    # ------------------------------------------------------------
    if model_type in ("llm", "embedding", "router"):
        model_name = model_info["model_name"]
        messages = [{"role": "user", "content": prompt}]
        try:
            return call_model(model_name, messages)
        except Exception as e:
            return f"[Model Executor Error] {e}"

    # ------------------------------------------------------------
    # Fallback stub executor
    # ------------------------------------------------------------
    return run_stubbed_model(prompt)


def run_stubbed_model(prompt: str) -> str:
    """
    Temporary fallback model executor.
    Extracts the user message from the prompt and returns a deterministic response.
    """

    parts = prompt.split("USER MESSAGE:")
    if len(parts) < 2:
        return "Model executor error: USER MESSAGE not found in prompt."

    user_section = parts[1]
    user_message = user_section.split("INSTRUCTIONS:")[0].strip()

    return (
        "[Stubbed Model Response]\n"
        f"You said: {user_message}"
    )
