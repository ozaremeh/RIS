# src/main.py

from router import handle_user_message
from memory_store import init_memory


def main():
    init_memory()
    print("Orchestrator demo. Type 'quit' to exit.")

    while True:
        user = input("\nYou: ")
        if user.strip().lower() in {"quit", "exit"}:
            break

        # Router now returns BOTH prompt and model response
        prompt, response = handle_user_message(user)

        print("\n--- MODEL PROMPT ---\n")
        print(prompt)

        print("\n--- MODEL RESPONSE ---\n")
        print(response)

        print("\n---------------------\n")


if __name__ == "__main__":
    main()

