#!/bin/bash
set -euo pipefail
umask 077
worktree=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
base="${1:-/home/web/seaparser/data/vinga-uddevalla-20261018}"
if (( $# > 0 )); then shift; fi
mkdir -p "$base"
exec 8>"$base/capture.lock"
flock -n 8 || exit 75
run_id="$(date -u +%Y%m%dT%H%M%SZ)-$$"
log="$base/$run_id.log"
printf 'Log: %s\nStatus: %s\n' "$log" "$base/status.json"
exec >>"$log" 2>&1
finish() { rc=$?; trap - EXIT; printf 'END=%s EXIT_CODE=%s\n' "$(date -u +%FT%TZ)" "$rc"; printf '%s\n' "$rc" >"$base/$run_id.exit"; }
trap finish EXIT
printf 'START=%s CWD=%s\n' "$(date -u +%FT%TZ)" "$worktree"
cd "$worktree"
unset COPERNICUSMARINE_SERVICE_USERNAME COPERNICUSMARINE_SERVICE_PASSWORD
timeout --signal=TERM --kill-after=10s 3600 "$worktree/.venv/bin/python" -B -m scripts.fetch_uddevalla --output "$base" "$@" </dev/null
