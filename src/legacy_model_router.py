# src/model_router.py

import re

QWEN_MODEL = "qwen2.5-7b-instruct"
DEEPSEEK_CODER_MODEL = "deepseek-coder-6.7b-instruct"


def is_code_task(text: str) -> bool:
    """
    Simple heuristic to detect coding/debugging tasks.
    This is scaffolding for the learned router.
    """

    code_keywords = [
        "python", "java", "c++", "javascript", "error", "traceback",
        "function", "class", "bug", "debug", "compile", "stack trace",
        "code", "script", "algorithm"
    ]

    # Code fences or obvious code blocks
    if "```" in text:
        return True

    lowered = text.lower()
    return any(keyword in lowered for keyword in code_keywords)


def choose_model(user_message: str) -> str:
    """
    Decide which LLM to call based on the content of the message.
    """

    if is_code_task(user_message):
        return DEEPSEEK_CODER_MODEL

    return QWEN_MODEL

