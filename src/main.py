# src/main.py

import sys
from router import handle_user_message
from memory_store import init_memory

# NEW: import the ingestion pipeline
from ingestion.pipeline import PaperIngestionPipeline


def run_code_ingestion():
    print("Running code ingestion...")
    pipeline = PaperIngestionPipeline()
    result = pipeline.ingest_codebase()
    print("\n--- CODE INGESTION RESULT ---\n")
    print(result)
    print("\n-----------------------------\n")


def main():
    # Optional CLI flag
    if "--ingest-code" in sys.argv:
        run_code_ingestion()
        return

    init_memory()
    print("Orchestrator demo. Type 'quit' to exit.")

    while True:
        user = input("\nYou: ")
        if user.strip().lower() in {"quit", "exit"}:
            break

        # Router returns BOTH prompt and model response
        prompt, response = handle_user_message(user)

        print("\n--- MODEL PROMPT ---\n")
        print(prompt)

        print("\n--- MODEL RESPONSE ---\n")
        print(response)

        print("\n---------------------\n")


if __name__ == "__main__":
    main()
