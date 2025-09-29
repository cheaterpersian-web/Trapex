#!/usr/bin/env bash
set -euo pipefail

VENV_DIR=".venv"
if [ -d "$VENV_DIR" ]; then
  # shellcheck disable=SC1090
  source "$VENV_DIR/bin/activate"
fi

exec python3 tools/hsv_calibrator.py "$@"
