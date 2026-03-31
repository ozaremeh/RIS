# retrieval_architecture/utils.py

from pathlib import Path

def module_to_path(module: str) -> Path | None:
    root = Path(__file__).parent.parent
    parts = module.split(".")
    path = root.joinpath(*parts).with_suffix(".py")
    return path if path.exists() else None
