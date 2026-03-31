# src/api_client.py

import requests
from typing import List, Dict, Generator
import json

# ---------------------------------------------------------------------
# LM Studio OpenAI-compatible endpoint
# ---------------------------------------------------------------------

LMSTUDIO_API_URL = "http://localhost:1234/v1/chat/completions"


# ---------------------------------------------------------------------
# Non-streaming model call
# ---------------------------------------------------------------------

def call_model(model_name: str, messages: List[Dict[str, str]]) -> str:
    """
    Send a non-streaming chat completion request to LM Studio.
    """

    payload = {
        "model": model_name,
        "messages": messages,
        "temperature": 0.7,
        "stream": False,
    }

    try:
        response = requests.post(LMSTUDIO_API_URL, json=payload)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Error communicating with LM Studio: {e}")

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Unexpected response format from LM Studio: {data}") from e


# ---------------------------------------------------------------------
# Streaming model call (currently implemented as non-streaming fallback)
# ---------------------------------------------------------------------

def stream_model(
    model_name: str,
    messages: List[Dict[str, str]],
) -> Generator[str, None, None]:
    """
    Streaming interface placeholder.

    For now, this performs a non-streaming request and yields the full
    response once. This keeps the orchestrator interface stable while
    avoiding LM Studio streaming edge cases.
    """

    payload = {
        "model": model_name,
        "messages": messages,
        "temperature": 0.7,
        "stream": False,
    }

    try:
        response = requests.post(LMSTUDIO_API_URL, json=payload)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Streaming error communicating with LM Studio: {e}")

    try:
        text = data["choices"][0]["message"]["content"]
        yield text
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Unexpected response format from LM Studio: {data}") from e

def get_loaded_models():
    """
    Placeholder for GUI compatibility.

    RIS no longer manages model loading state.
    LM Studio owns model lifecycle.
    """
    return []
