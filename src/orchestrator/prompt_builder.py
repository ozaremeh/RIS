# src/orchestrator/prompt_builder.py
"""
Prompt construction module for the orchestrator.

Responsibilities:
- Build the enriched user prompt
- Inject semantic + episodic memory
- Apply system-level instructions
- Keep orchestrator.py clean and modular
"""

from typing import List

from semantic_memory import retrieve_semantic_memory
from memory import retrieve_relevant_memory
from orchestrator.logging import log_event


def build_orchestrator_prompt(
    user_message: str,
    retrieval_mode: str,
) -> str:
    """
    Builds the enriched user prompt, including:
      - semantic memory retrieval
      - episodic memory retrieval
      - memory block formatting

    Returns:
      full_user_prompt: str
    """

    # ------------------------------------------------------------
    # 1. Base prompt is now just the user message
    # (old project router removed)
    # ------------------------------------------------------------
    prompt = user_message

    log_event("Built base orchestrator prompt", {
        "prompt_preview": prompt[:200] + "..."
    })

    # ------------------------------------------------------------
    # 2. Retrieve SEMANTIC memory
    # ------------------------------------------------------------
    try:
        semantic_chunks: List[str] = retrieve_semantic_memory(user_message, k=3)
    except Exception as e:
        semantic_chunks = []
        log_event("Semantic memory retrieval failed", {"error": str(e)})

    # ------------------------------------------------------------
    # 3. Retrieve EPISODIC memory
    # ------------------------------------------------------------
    try:
        episodic_chunks: List[str] = retrieve_relevant_memory(user_message, retrieval_mode)
    except Exception as e:
        episodic_chunks = []
        log_event("Episodic memory retrieval failed", {"error": str(e)})

    # ------------------------------------------------------------
    # 4. Build memory blocks
    # ------------------------------------------------------------
    memory_sections: List[str] = []

    if semantic_chunks:
        semantic_block = "SEMANTIC MEMORY:\n" + "\n".join(f"- {fact}" for fact in semantic_chunks)
        memory_sections.append(semantic_block)

    if episodic_chunks:
        episodic_block = "EPISODIC MEMORY:\n" + "\n".join(f"- {chunk}" for chunk in episodic_chunks)
        memory_sections.append(episodic_block)

    # ------------------------------------------------------------
    # 5. Combine memory + current request
    # ------------------------------------------------------------
    if memory_sections:
        memory_text = "\n\n".join(memory_sections)
        full_user_prompt = (
            "You have access to prior memory.\n"
            "Use SEMANTIC MEMORY for stable facts and preferences.\n"
            "Use EPISODIC MEMORY only when clearly relevant.\n"
            "Do not invent memory.\n\n"
            f"{memory_text}\n\n"
            f"CURRENT USER REQUEST:\n{prompt}"
        )
    else:
        full_user_prompt = prompt

    return full_user_prompt
