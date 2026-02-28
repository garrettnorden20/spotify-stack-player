#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [[ ! -f ".venv-tk/bin/activate" ]]; then
  echo "Missing .venv-tk. Create it first." >&2
  exit 1
fi

source .venv-tk/bin/activate

if [[ "${1:-}" == "--hotkeys" ]]; then
  SP_STACK_HOTKEYS=1 exec python main.py
else
  exec python main.py
fi
