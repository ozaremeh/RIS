import os
import ast
import sys
import stdlib_list

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")

# Get list of stdlib modules for your Python version
stdlib = set(stdlib_list.stdlib_list(f"{sys.version_info.major}.{sys.version_info.minor}"))

# Your own top-level packages (adjust if needed)
LOCAL_PACKAGES = {"gui", "orchestrator", "ingestion", "src"}

third_party = set()

def is_local(name):
    return name.split(".")[0] in LOCAL_PACKAGES

def scan_file(path):
    with open(path, "r", encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read(), filename=path)
        except SyntaxError:
            return

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name.split(".")[0]
                if name not in stdlib and not is_local(name):
                    third_party.add(name)

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                name = node.module.split(".")[0]
                if name not in stdlib and not is_local(name):
                    third_party.add(name)

def walk_src():
    for root, _, files in os.walk(SRC_DIR):
        for f in files:
            if f.endswith(".py"):
                scan_file(os.path.join(root, f))

if __name__ == "__main__":
    walk_src()
    print("\n=== Third-party imports detected ===")
    for pkg in sorted(third_party):
        print(pkg)
