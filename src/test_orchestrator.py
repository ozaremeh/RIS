from .orchestrator import send_message, reset_history

def run_test():
    reset_history()

    print("=== Turn 1 ===")
    print(send_message("Help me think about a project involving EphA2 and cancer progression."))

    print("\n=== Turn 2 (follow-up) ===")
    print(send_message("Given that, what would be a good first experiment to run?"))

if __name__ == "__main__":
    run_test()

