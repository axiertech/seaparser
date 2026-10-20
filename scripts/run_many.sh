#!/bin/bash
# scripts/run_many.sh
set -e
for task in "$@"; do
    cp "$task" ~/app/AUTONOMOUS_TASK.md
    python -B -m scripts.runner --fast || { echo "runner misslyckades för $task"; exit 1; }
    # hitta senaste run i RUN_HISTORY.json
    run=$(python -c "import json; print(json.load(open('RUN_HISTORY.json'))['runs'][-1]['run'])")
    date=$(python -c "import json; print(json.load(open('RUN_HISTORY.json'))['runs'][-1]['date'])")
    python -B -m scripts.verify_run "${date}_${run}" --fast || { echo "verify_run misslyckades"; exit 1; }
done
