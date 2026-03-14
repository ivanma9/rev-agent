#!/usr/bin/env bash
# run_agent.sh — Start the Rev autonomous scheduler
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate virtualenv
if [ -d "$SCRIPT_DIR/.venv" ]; then
    source "$SCRIPT_DIR/.venv/bin/activate"
elif [ -d "$SCRIPT_DIR/venv" ]; then
    source "$SCRIPT_DIR/venv/bin/activate"
else
    echo "ERROR: No virtualenv found at .venv or venv" >&2
    exit 1
fi

export PYTHONPATH="$SCRIPT_DIR"

mkdir -p "$SCRIPT_DIR/logs"

# Graceful shutdown on SIGTERM
trap 'echo "Received SIGTERM, shutting down..."; kill "$CHILD_PID" 2>/dev/null; wait "$CHILD_PID" 2>/dev/null; exit 0' SIGTERM

echo "Starting Rev scheduler at $(date)"
python -m src.scheduler &
CHILD_PID=$!
wait "$CHILD_PID"
