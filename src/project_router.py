# src/router.py

from typing import Tuple, List

from assignment import assign_projects, current_model_id
from retrieval import retrieve_relevant_chunks
from memory_store import log_message
from classifier import reasoning_type, topic_label
from config import MODEL_ID


def build_prompt(
    message: str,
    assigned_projects: List[str],
    project_weights: dict,
    retrieved_memory,
) -> str:
    """
    Construct the full prompt shown in tests.test_end_to_end.
    """
    lines = []

    lines.append("SYSTEM:")
    lines.append("You are an AI assistant operating inside a modular orchestrator system.")
    lines.append("Your behavior must be consistent, structured, and aligned with the assigned project domains.")
    lines.append("You have access to retrieved memory, project context, and reasoning metadata.")
    lines.append("")
    lines.append("PROJECT CONTEXT:")
    lines.append(f"Assigned projects: {assigned_projects}")
    lines.append(f"Project weights: {project_weights}")
    lines.append("")
    lines.append("RETRIEVED MEMORY:")

    if not retrieved_memory:
        lines.append("- <no relevant memory>")
    else:
        for entry in retrieved_memory:
            proj_labels = entry.assigned
            lines.append(
                f"- {proj_labels} (weight={entry.weights}, time={entry.timestamp}): {entry.text}"
            )

    lines.append("")
    lines.append("REASONING METADATA:")
    lines.append(f"Reasoning type: {reasoning_type(message)}")
    lines.append(f"Topic: {topic_label(message)}")
    lines.append(f"Model ID: {MODEL_ID}")
    lines.append("")
    lines.append("USER MESSAGE:")
    lines.append(message)
    lines.append("")
    lines.append("INSTRUCTIONS:")
    lines.append("Provide a helpful, domain‑appropriate response.")
    lines.append("Use the retrieved memory when relevant.")
    lines.append("Do not hallucinate or invent details not supported by memory or the user message.")

    return "\n".join(lines)


def handle_user_message(message: str) -> Tuple[str, str]:
    """
    Main entry point for the orchestrator.

    Correct ordering:
      1. Assign projects.
      2. Retrieve memory (before writing new entry).
      3. Build prompt.
      4. Generate stubbed response.
      5. Write new memory entry last.
    """

    # 1. Project assignment
    assigned_projects, project_weights = assign_projects(message)

    # Determine primary project index for retrieval
    if project_weights:
        primary_idx = max(project_weights.items(), key=lambda kv: kv[1])[0]
        target_project_idx = int(primary_idx)
    else:
        target_project_idx = 0

    # 2. Retrieve BEFORE writing new memory
    retrieved = retrieve_relevant_chunks(
        query=message,
        target_project=target_project_idx,
    )

    # 3. Build prompt
    prompt = build_prompt(
        message=message,
        assigned_projects=assigned_projects,
        project_weights=project_weights,
        retrieved_memory=retrieved,
    )

    # 4. Stubbed model response
    response = f"[Stubbed Model Response]\nYou said: {message}"

    # 5. Write memory AFTER retrieval
    log_message(
        text=message,
        scores_raw=[],  # tests don't use this field
        assigned=[int(p) for p in assigned_projects],
        weights={int(k): float(v) for k, v in project_weights.items()},
        reasoning_type=reasoning_type(message),
        topic=topic_label(message),
        model_id=MODEL_ID,
    )

    return prompt, response
