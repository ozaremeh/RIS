# src/model_registry.py

"""
Central registry of all models used in the system.
Supports multi-model parallelism and LM Studio orchestration.
"""

MODEL_REGISTRY = {
    "writer": {
        "model_name": "qwen/qwen3-32b",
        "port": 8002,
        "type": "llm",
        "role": "writing",
        "max_context": 32768,
    },
    "reasoner": {
        "model_name": "phi-4-reasoning",
        "port": 8001,
        "type": "llm",
        "role": "reasoning",
        "max_context": 16384,
    },
    "coder": {
        "model_name": "deepseek-coder-6.7b-instruct-mlx",
        "port": 8003,
        "type": "llm",
        "role": "coding",
        "max_context": 8192,
    },

    # ⭐ Math specialist model
    "math": {
        "model_name": "qwen2.5-math-7b-instruct",
        "port": 8006,
        "type": "llm",
        "role": "math",
        "max_context": 8192,
    },

    "embedder": {
        "model_name": "bge-small-en-v1.5",
        "port": 8004,
        "type": "embedding",
        "role": "embedding",
        "embedding_dim": 384,
    },

    "router": {
        "model_name": "phi-3-mini-4k-instruct-mlx",
        "port": 8005,
        "type": "router",
        "role": "routing",
    },

    # ⭐ NEW: Architecture retrieval model (internal, no port)
    "architecture": {
        "model_name": "qwen/qwen3-32b",
        "type": "internal",
        "role": "architecture",
    },
}


# ------------------------------------------------------------
# Accessors
# ------------------------------------------------------------

def get_model(name: str) -> dict:
    if name not in MODEL_REGISTRY:
        raise KeyError(f"Unknown model '{name}'. Available models: {list(MODEL_REGISTRY.keys())}")
    return MODEL_REGISTRY[name]


def get_port(name: str) -> int:
    """
    Only LLMs and embedding models have ports.
    Internal models (like architecture) do not.
    """
    model = MODEL_REGISTRY[name]
    if "port" not in model:
        raise KeyError(f"Model '{name}' does not have a port (type={model['type']}).")
    return model["port"]


def get_model_name(name: str) -> str:
    return MODEL_REGISTRY[name]["model_name"]


def list_models():
    return list(MODEL_REGISTRY.keys())


def list_llms():
    return [k for k, v in MODEL_REGISTRY.items() if v["type"] == "llm"]
