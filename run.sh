#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f "venv/bin/python" ]; then
    exec "venv/bin/python" main.py "$@"
elif [ -f ".venv/bin/python" ]; then
    exec ".venv/bin/python" main.py "$@"
elif [ -f "src/.venv/bin/python" ]; then
    exec "src/.venv/bin/python" main.py "$@"
elif command -v python3 &>/dev/null; then
    exec python3 main.py "$@"
elif command -v python &>/dev/null; then
    exec python main.py "$@"
else
    echo "Error: Python was not found in PATH or virtual environments." >&2
    exit 1
fi
