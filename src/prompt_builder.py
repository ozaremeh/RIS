# src/prompt_builder.py

from typing import List, Dict
from memory_store import MemoryEntry
from config import PROJECTS

# ============================================================
# ROUTING PROMPT (NEW — REQUIRED BY choose_model_learned)
# ============================================================

ROUTING_PROMPT = """
You are a routing classifier for a multi‑model AI system.

Your job is to classify the user's message into one of the following intents:

- coding
- math
- reasoning_light
- reasoning_deep
- writing
- retrieval
- architecture
- general

Examples:

USER: "Explain the dependency graph of your ingestion pipeline."
INTENT: "architecture"

USER: "How are you built? Describe your system architecture."
INTENT: "architecture"

USER: "What modules make up your orchestrator?"
INTENT: "architecture"

USER: "Show me the structure of your codebase."
INTENT: "architecture"

USER: "Write a Python function to parse FASTA files."
INTENT: "coding"

USER: "Differentiate x^2 * sin(x)."
INTENT: "math"

USER: "Summarize the findings across these papers."
INTENT: "retrieval"

USER: "Explain why CRISPR off‑target effects occur."
INTENT: "reasoning_light"

USER: "Generate a detailed hypothesis about EphA2 signaling."
INTENT: "reasoning_deep"

USER: "Draft a paragraph for my F31 application."
INTENT: "writing"

Now classify the following user message:

\"{message}\"

Return ONLY a JSON object with:
- intent
- confidence
- task_type (optional)
- complexity (optional)
"""


# ============================================================
# ORCHESTRATOR PROMPT BUILDER (unchanged)
# ============================================================

def _project_names(indices: List[int]) -> List[str]:
    return [PROJECTS[i] for i in indices]


def _format_weights(weights: Dict[int, float]) -> Dict[str, float]:
    return {str(k): float(v) for k, v in weights.items()}


def build_prompt(
    user_message: str,
    assigned_projects: List[int],
    weights: Dict[int, float],
    retrieved_entries: List[MemoryEntry],
    reasoning_type: str,
    topic: str,
    model_id: str,
) -> str:
    assigned_names = _project_names(assigned_projects)
    weight_map = _format_weights(weights)

    lines = []

    # SYSTEM
    lines.append("SYSTEM:")
    lines.append("You are an AI assistant operating inside a modular orchestrator system.")
    lines.append("Your behavior must be consistent, structured, and aligned with the assigned project domains.")
    lines.append("You have access to retrieved memory, project context, and reasoning metadata.")
    lines.append("")

    # PROJECT CONTEXT
    lines.append("PROJECT CONTEXT:")
    lines.append(f"Assigned projects: {assigned_names}")
    lines.append(f"Project weights: {weight_map}")
    lines.append("")

    # RETRIEVED MEMORY
    lines.append("RETRIEVED MEMORY:")
    if not retrieved_entries:
        lines.append("(no relevant memory found)")
    else:
        for entry in retrieved_entries:
            tags = _project_names(entry.assigned)
            lines.append(
                f"- {tags} "
                f"(weight={entry.weights}, time={entry.timestamp}): "
                f"{entry.text}"
            )
    lines.append("")

    # REASONING METADATA
    lines.append("REASONING METADATA:")
    lines.append(f"Reasoning type: {reasoning_type}")
    lines.append(f"Topic: {topic}")
    lines.append(f"Model ID: {model_id}")
    lines.append("")

    # USER MESSAGE
    lines.append("USER MESSAGE:")
    lines.append(user_message)
    lines.append("")

    # INSTRUCTIONS
    lines.append("INSTRUCTIONS:")
    lines.append("Provide a helpful, domain‑appropriate response.")
    lines.append("Use the retrieved memory when relevant.")
    lines.append("Do not hallucinate or invent details not supported by memory or the user message.")

    return "\n".join(lines)
