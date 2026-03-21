# src/model_registry.py

"""
Central registry of all models used in the system.
Supports multi-model parallelism and LM Studio orchestration.
"""

MODEL_REGISTRY = {
    "writer": {
        "model_name": "qwen2.5-72b-instruct",
        "port": 8002,
        "type": "llm",
        "role": "writing",
        "max_context": 32768,
    },
    "reasoner": {
        "model_name": "microsoft_Phi-4-reasoning-plus-Q5_K_M",
        "port": 8001,
        "type": "llm",
        "role": "reasoning",
        "max_context": 16384,
    },
    "coder": {
        "model_name": "deepseek-coder-6.7b-instruct",
        "port": 8003,
        "type": "llm",
        "role": "coding",
        "max_context": 8192,
    },

    # ⭐ NEW: Math specialist model
    "math": {
        "model_name": "deepseek-math-7b-instruct.Q5_K_M",
        "port": 8006,                 # choose a free port
        "type": "llm",
        "role": "math",
        "max_context": 8192,
        "local_path": "~/llama.cpp/models/deepseek-math-7b-instruct.Q5_K_M.gguf",
    },

    "embedder": {
        "model_name": "bge-small-en-v1.5",
        "port": 8004,
        "type": "embedding",
        "role": "embedding",
        "embedding_dim": 384,
    },
    "router": {
        "model_name": "phi-3-mini-4k-instruct",
        "port": 8005,
        "type": "router",
        "role": "routing",
    },
}

def get_model(name: str) -> dict:
    return MODEL_REGISTRY.get(name, MODEL_REGISTRY["reasoner"])

def get_port(name: str) -> int:
    return MODEL_REGISTRY[name]["port"]

def get_model_name(name: str) -> str:
    return MODEL_REGISTRY[name]["model_name"]

def list_models():
    return list(MODEL_REGISTRY.keys())

def list_llms():
    return [k for k, v in MODEL_REGISTRY.items() if v["type"] == "llm"]
