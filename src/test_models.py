from api_client import call_model

def test_qwen():
    messages = [
        {"role": "system", "content": "You are Qwen with a clear, direct, Real-Talk style."},
        {"role": "user", "content": "Give me a one-sentence explanation of what you're good at."}
    ]

    print("\n--- Qwen Response ---")
    reply = call_model("qwen2.5-7b-instruct", messages)
    print(reply)


def test_deepseek():
    messages = [
        {"role": "system", "content": "You are DeepSeek-Coder, a focused coding and debugging specialist."},
        {"role": "user", "content": "Write a Python function that returns the first 10 Fibonacci numbers."}
    ]

    print("\n--- DeepSeek-Coder Response ---")
    reply = call_model("deepseek-coder-6.7b-instruct", messages)
    print(reply)


if __name__ == "__main__":
    test_qwen()
    test_deepseek()

