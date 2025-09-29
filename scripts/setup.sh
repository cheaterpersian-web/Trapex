#!/usr/bin/env bash
set -euo pipefail

# Simple setup for Python venv and dependencies
PY=python3
VENV_DIR=".venv"

if ! command -v "$PY" >/dev/null 2>&1; then
  echo "python3 not found. Please install Python 3.9+ and re-run." >&2
  exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
  "$PY" -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt

echo "Setup complete. Activate with: source $VENV_DIR/bin/activate"
