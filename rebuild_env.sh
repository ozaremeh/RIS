#!/usr/bin/env bash

set -e

ENV_NAME="ris311"
PY_VERSION="3.11"
REQ_FILE="requirements.txt"

echo "=== Research Intelligence System: Environment Rebuild ==="
echo "Target environment: $ENV_NAME"
echo

# ------------------------------------------------------------
# 1. Remove old environment if it exists
# ------------------------------------------------------------
if conda env list | grep -q "^$ENV_NAME "; then
    echo "Removing existing environment: $ENV_NAME"
    conda remove -n "$ENV_NAME" --all -y
else
    echo "No existing environment named $ENV_NAME found."
fi

echo

# ------------------------------------------------------------
# 2. Create fresh environment
# ------------------------------------------------------------
echo "Creating new environment: $ENV_NAME (Python $PY_VERSION)"
conda create -n "$ENV_NAME" python="$PY_VERSION" -y
echo

# ------------------------------------------------------------
# 3. Activate environment
# ------------------------------------------------------------
echo "Activating environment..."
# shellcheck disable=SC1091
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "$ENV_NAME"
echo

# ------------------------------------------------------------
# 4. Install dependencies
# ------------------------------------------------------------
if [ ! -f "$REQ_FILE" ]; then
    echo "ERROR: requirements.txt not found in current directory."
    exit 1
fi

echo "Installing dependencies from $REQ_FILE..."
pip install -r "$REQ_FILE"
echo

# ------------------------------------------------------------
# 5. Install RIS package in editable mode
# ------------------------------------------------------------
echo "Installing RIS package in editable mode..."
pip install -e .
echo

# ------------------------------------------------------------
# 6. Success message
# ------------------------------------------------------------
echo "=========================================================="
echo "Environment '$ENV_NAME' rebuilt successfully!"
echo "Activate it with:"
echo "    conda activate $ENV_NAME"
echo "Run RIS with:"
echo "    RIS"
echo "=========================================================="
