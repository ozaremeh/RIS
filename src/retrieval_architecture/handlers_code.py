# retrieval_architecture/handlers_code.py

from pathlib import Path
import ast
from retrieval_architecture.utils import module_to_path


def handle_show_code_query(prompt: str):
    lower = prompt.lower()

    # detect module
    if "module" in lower:
        name = lower.split("module")[-1].strip()
        path = module_to_path(name)
        if path and path.exists():
            return {"code": path.read_text()}
        return {"error": f"Module '{name}' not found."}

    # detect function
    for token in lower.split():
        if "." in token:
            return {"code": extract_function_code(token)}

    return {"error": "Could not determine which code to show."}


def extract_function_code(fq_name: str) -> str:
    if "." not in fq_name:
        return f"Invalid function name '{fq_name}'."

    module, func = fq_name.rsplit(".", 1)
    path = module_to_path(module)
    if not path:
        return f"Module '{module}' not found."

    text = path.read_text()
    tree = ast.parse(text)
    lines = text.splitlines()

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func:
            start = node.lineno - 1
            end = getattr(node, "end_lineno", start)
            return "\n".join(lines[start:end])

    return f"Function '{func}' not found in module '{module}'."
