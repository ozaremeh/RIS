# src/api_client.py

import requests
from typing import List, Dict, Generator
import json

from llama_server_manager import (
    launch_llama_server_if_needed,
    stop_llama_server,
)

# ---------------------------------------------------------------------
# LM Studio endpoints
# ---------------------------------------------------------------------

LMSTUDIO_API_URL = "http://localhost:1234/v1/chat/completions"
LMSTUDIO_MODELS_URL = "http://localhost:1234/v1/models"
LMSTUDIO_LOAD_URL = "http://localhost:1234/v1/models/load"
LMSTUDIO_UNLOAD_URL = "http://localhost:1234/v1/models/unload"

# ---------------------------------------------------------------------
# Endpoint override for models served by llama.cpp
# ---------------------------------------------------------------------

MODEL_ENDPOINTS = {
    # Qwen2.5 72B Writer (GGUF)
    "writer": "http://localhost:8080/v1/chat/completions",

    # DeepSeek Math 7B (GGUF)
    "math": "http://localhost:8090/v1/chat/completions",
}

# ---------------------------------------------------------------------
# Model Loading Helpers
# ---------------------------------------------------------------------

def is_model_loaded(model_name: str) -> bool:
    """
    Returns True if LM Studio reports the model as loaded.
    GGUF models (served by llama.cpp) are considered loaded if the server is running.
    """
    if model_name in MODEL_ENDPOINTS:
        # GGUF model → check if llama.cpp server is running
        try:
            health_url = MODEL_ENDPOINTS[model_name].replace("/v1/chat/completions", "/health")
            resp = requests.get(health_url)
            return resp.status_code == 200
        except Exception:
            return False

    # LM Studio model
    try:
        resp = requests.get(LMSTUDIO_MODELS_URL)
        resp.raise_for_status()
        data = resp.json()

        for m in data.get("data", []):
            if m.get("id") == model_name:
                return m.get("loaded", False)

    except Exception:
        return False

    return False


def get_loaded_models() -> List[str]:
    """
    Returns a list of currently loaded models.
    Works for both LM Studio and llama.cpp.
    """
    loaded = []

    # LM Studio models
    try:
        resp = requests.get(LMSTUDIO_MODELS_URL)
        resp.raise_for_status()
        data = resp.json()

        for m in data.get("data", []):
            if m.get("loaded", False):
                loaded.append(m.get("id"))
    except Exception:
        pass

    # GGUF models
    for model_key, endpoint in MODEL_ENDPOINTS.items():
        try:
            health_url = endpoint.replace("/v1/chat/completions", "/health")
            resp = requests.get(health_url)
            if resp.status_code == 200:
                loaded.append(model_key)
        except Exception:
            pass

    return loaded


def load_model(model_name: str) -> None:
    """
    Explicitly load a model into LM Studio memory.
    No-op for llama.cpp models.
    """
    if model_name in MODEL_ENDPOINTS:
        return

    try:
        resp = requests.post(LMSTUDIO_LOAD_URL, json={"model": model_name})
        resp.raise_for_status()
    except Exception as e:
        raise RuntimeError(f"Failed to load model '{model_name}': {e}")


def unload_model(model_name: str) -> None:
    """
    Unload LM Studio models or stop llama.cpp server for GGUF models.
    """
    if model_name in MODEL_ENDPOINTS:
        stop_llama_server()
        return

    try:
        resp = requests.post(LMSTUDIO_UNLOAD_URL, json={"model": model_name})
        resp.raise_for_status()
    except Exception as e:
        raise RuntimeError(f"Failed to unload model '{model_name}': {e}")


def load_model_if_needed(model_name: str) -> None:
    """
    Lazy-load: only load the model if it's not already loaded.
    """
    if not is_model_loaded(model_name):
        load_model(model_name)


# ---------------------------------------------------------------------
# Non-streaming model call
# ---------------------------------------------------------------------

def call_model(model_name: str, messages: List[Dict[str, str]]) -> str:
    """
    Non-streaming call.
    """

    payload = {
        "model": model_name,
        "messages": messages,
        "temperature": 0.7,
        "stream": False,
    }

    # Determine endpoint
    url = MODEL_ENDPOINTS.get(model_name, LMSTUDIO_API_URL)

    # Auto-launch llama.cpp server if needed
    if model_name in MODEL_ENDPOINTS:
        launch_llama_server_if_needed(model_name)

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Error communicating with backend: {e}")

    data = response.json()
    print(">>> CALL_MODEL RAW RESPONSE JSON:", json.dumps(data, indent=2))

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        raise RuntimeError(f"Unexpected response format: {data}")


# ---------------------------------------------------------------------
# Streaming model call
# ---------------------------------------------------------------------

def stream_model(model_name: str, messages: List[Dict[str, str]]):
    """
    TEMPORARY: Disable streaming to test backend compatibility.
    """

    # Force non-streaming call
    payload = {
        "model": model_name,
        "messages": messages,
        "temperature": 0.7,
        "stream": False,
    }

    url = MODEL_ENDPOINTS.get(model_name, LMSTUDIO_API_URL)

    # Auto-launch llama.cpp server if needed
    if model_name in MODEL_ENDPOINTS:
        launch_llama_server_if_needed(model_name)

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

        # Yield the full text once (so the orchestrator still works)
        text = data["choices"][0]["message"]["content"]
        yield text
        return text

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Streaming error communicating with backend: {e}")

