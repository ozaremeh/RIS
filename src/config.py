# src/config.py

"""
Global configuration for the orchestrator.

All tunable parameters live here so you can adjust behavior without
touching the core logic. Retrieval scoring, project assignment, and
model metadata are all centralized for clarity.

This file now also includes unified model configuration for:
- the learned router (Phi-3 Mini)
- coding model
- reasoning model
- general fallback model
- routing confidence thresholds
"""

# -------------------------------------------------------------------
# Project configuration
# -------------------------------------------------------------------

PROJECTS = [
    "orchestrator",
    "teaching",
    "research",
    "personal",
    "meta",
    "admin",
    "dnd",
    "wellbeing",
    "play",
]

# Descriptions used by the classifier to embed project semantics.
PROJECT_DESCRIPTIONS = {
    "orchestrator": "AI workflow, routing, memory, retrieval, scoring, and system design.",
    "teaching": "Pedagogy, course design, explanations, tutoring, and academic support.",
    "research": "EphA2 receptor, EphA2 signaling, cancer biology, molecular signaling, computational biology, scientific research projects.",
    "personal": "Personal tasks, life management, planning, and reflection.",
    "meta": "Questions about the orchestrator itself, debugging, architecture, and design.",
    "admin": "Logistics, scheduling, paperwork, and organizational tasks.",
    "dnd": "Dungeons & Dragons, worldbuilding, characters, rules, and storytelling.",
    "wellbeing": "Health, habits, exercise, mental clarity, and self-maintenance.",
    "play": "Games, hobbies, fun, exploration, and creative play.",
}

# Sigma-style assignment threshold.
TAU_EXCL = 0.55


# -------------------------------------------------------------------
# Model configuration (NEW unified section)
# -------------------------------------------------------------------

# Router model (Qwen2.5-1.5B Instruct)
ROUTER_MODEL = "qwen2.5-1.5b-instruct-mlx"

# Specialist models
CODING_MODEL = "deepseek-coder-6.7b-instruct"
REASONING_MODEL = "qwen2.5-7b-instruct"
GENERAL_MODEL = "qwen2.5-7b-instruct"   # fallback for anything not coding

# Minimum confidence required before trusting the router's decision.
ROUTER_CONFIDENCE_THRESHOLD = 0.55


# -------------------------------------------------------------------
# Orchestrator metadata
# -------------------------------------------------------------------

MODEL_ID = "orchestrator-v0.1"


# -------------------------------------------------------------------
# Retrieval configuration
# -------------------------------------------------------------------

TOP_K = 5

ALPHA = 0.4
BETA = 0.05
GAMMA = 0.0
DELTA = 4.0

SIM_GAMMA = 6.0
RECENCY_ETA = 2.0

RECENCY_LAMBDA = 1e-5

# src/config.py

import os

# Absolute path to the project root (the "core" directory)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# You can add other global config values here as needed

