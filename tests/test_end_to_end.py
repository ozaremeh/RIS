# tests/test_end_to_end.py

import time

from src.memory_store import init_memory, MEMORY_LOG
from src.router import handle_user_message
from src.vector_store import VECTOR_STORE
from src.retrieval import retrieve_relevant_chunks
from src.assignment import assign_projects
from src.embeddings import embed_text


def print_header(title: str):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80 + "\n")


def test_message(msg: str):
    print_header(f"USER MESSAGE: {msg}")

    # Run full orchestrator pipeline
    prompt, response = handle_user_message(msg)

    print("---- PROMPT ----")
    print(prompt)
    print("\n---- RESPONSE ----")
    print(response)

    print("\n---- MEMORY COUNT ----")
    print(len(MEMORY_LOG))

    print("\n---- VECTOR STORE COUNT ----")
    print(len(VECTOR_STORE.entries))

    # Show top retrieval results for debugging
    assigned, _ = assign_projects(msg)
    target = assigned[0]

    print("\n---- TOP RETRIEVAL ----")
    chunks = retrieve_relevant_chunks(msg, target_project=target, k=5)
    for c in chunks:
        print(f"[{c.assigned}] {c.text} (t={c.timestamp})")

    print("\n")


def main():
    print_header("INITIALIZING MEMORY")
    init_memory()
    print(f"Loaded {len(MEMORY_LOG)} memory entries.")
    print(f"Vector store contains {len(VECTOR_STORE.entries)} embeddings.\n")

    # Test messages in sequence
    messages = [
        "I need to prep a DnD session.",
        "I'm worried about teaching this semester.",
        "Let's work on the orchestrator memory system.",
        "Oh, I wish I was a little slice of orange.",
        "What should I do for my DnD game?",
        "Help me think about the EphA2 project.",
    ]

    for msg in messages:
        test_message(msg)
        time.sleep(0.2)  # small delay for timestamp separation


if __name__ == "__main__":
    main()

