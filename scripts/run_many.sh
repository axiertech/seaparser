#!/bin/bash
# run_many.sh - run a sequence of autonomous tasks for a given root.
#
# Usage:  ./scripts/run_many.sh --root autonomy task1.md task2.md ...
#
# Each task file is copied to <root>/AUTONOMOUS_TASK.md, run with
# scripts.runner --root <root> --fast, then verified and merged with
# scripts.verify_run --root <root> --fast. Stops at the first failure.
# Never pushes. Never merges to main.
set -euo pipefail

ROOT="app"
if [[ "${1:-}" == "--root" ]]; then
    ROOT="$2"
    shift 2
fi

if [[ $# -eq 0 ]]; then
    echo "Usage: $0 [--root app|autonomy] task1.md task2.md ..." >&2
    exit 64
fi

APP_DIR=/home/web/seaparser/app
PYTHON="$APP_DIR/.venv/bin/python"
TASK_DEST="/home/web/seaparser/${ROOT}/AUTONOMOUS_TASK.md"

for task in "$@"; do
    echo ""
    echo "=========================================="
    echo "Running: $task -> $TASK_DEST"
    echo "=========================================="

    cp "$task" "$TASK_DEST"

    cd "$APP_DIR"
    if ! "$PYTHON" -B -m scripts.runner --root "$ROOT" --fast; then
        echo "FAILED: runner.py for $task" >&2
        echo "Task file kept at $TASK_DEST for inspection" >&2
        exit 1
    fi

    RUN_INFO=$("$PYTHON" - <<PYEOF
import json
from pathlib import Path
h = json.loads(Path("/home/web/seaparser/${ROOT}/RUN_HISTORY.json").read_text())
r = h["runs"][-1]
print(f"{r['date']}_{r['run']}")
PYEOF
)

    echo ""
    echo "Verifying and merging run $RUN_INFO"
    if ! "$PYTHON" -B -m scripts.verify_run --root "$ROOT" "$RUN_INFO" --fast; then
        echo "FAILED: verify_run for $task (run $RUN_INFO)" >&2
        exit 1
    fi

    echo "OK: $task completed as run $RUN_INFO"
done

echo ""
echo "All tasks completed."
