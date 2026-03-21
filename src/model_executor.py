# src/model_executor.py

def run_model(prompt: str) -> str:
    """
    Temporary model executor.
    For now, returns a simple deterministic response.
    Later, this will call a real model (MLX, llama.cpp, etc.).
    """

    # Extract the user message from the prompt
    parts = prompt.split("USER MESSAGE:")
    if len(parts) < 2:
        return "Model executor error: USER MESSAGE not found in prompt."

    user_section = parts[1]
    user_message = user_section.split("INSTRUCTIONS:")[0].strip()

    return (
        "[Stubbed Model Response]\n"
        f"You said: {user_message}"
    )

