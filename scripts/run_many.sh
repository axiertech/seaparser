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
FAILED_TASKS=""

for task in "$@"; do
    echo ""
    echo "=========================================="
    echo "Running: $task -> $TASK_DEST"
    echo "=========================================="

    if [ ! -f "$task" ]; then
        echo "FAILED: task file not found: $task" >&2
        exit 64
    fi

    cp "$task" "$TASK_DEST"

    cd "$APP_DIR"

    # Validate the task file before running it (checks Allowed files against base tree)
    if ! "$PYTHON" -B -m scripts.runner --root "$ROOT" --check; then
        echo "FAILED: Task sanity check failed for $task - skipping" >&2
        FAILED_TASKS="$FAILED_TASKS\n  - $task (sanity check failed)"
        continue
    fi

    # Skip tasks whose SHA-256 is already marked completed in RUN_HISTORY.json.
    # Without this, one already-run task blocks the whole queue.
    SKIP_INFO=$("$PYTHON" - <<PYEOF
import hashlib, json
from pathlib import Path
task_text = Path("$TASK_DEST").read_text()
sha = hashlib.sha256(task_text.strip().encode("utf-8")).hexdigest()
h = json.loads(Path("/home/web/seaparser/${ROOT}/RUN_HISTORY.json").read_text())
for r in h["runs"]:
    if r.get("task_sha256") == sha and r.get("status") == "completed":
        print(f"SKIP {r['date']}_{r['run']} {(r.get('commit') or '?')[:10]}")
        break
PYEOF
)
    if [[ "$SKIP_INFO" == SKIP* ]]; then
        echo "$SKIP_INFO - skipping $task"
        continue
    fi

    if ! "$PYTHON" -B -m scripts.runner --root "$ROOT" --fast; then
        echo "FAILED: runner.py for $task - continuing to next task" >&2
        FAILED_TASKS="$FAILED_TASKS\n  - $task"
        continue
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
if [ -n "$FAILED_TASKS" ]; then
    echo "Queue finished with failures:$FAILED_TASKS"
    exit 1
else
    echo "All tasks completed successfully."
fi
