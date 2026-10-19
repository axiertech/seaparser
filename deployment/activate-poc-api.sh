#!/bin/bash
# Add the isolated PoC API using the existing Apache proxy; retain the legacy API.
set -euo pipefail
/usr/bin/test "$(/usr/bin/id -u)" -eq 0
umask 022
exec 9<>/home/web/seaparser/autonomy/run.lock
/usr/bin/flock -n 9 || { /usr/bin/printf '%s\n' 'SeaParser work/activation lock is held; retry after the active task ends.' >&2; exit 1; }
poc_stage="$(cd -- "$(dirname -- "$0")" && pwd)"
poc_release="$(/usr/bin/python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["release"])' "$poc_stage/manifest.json")"
cd "$poc_stage/release"
exec > >(/usr/bin/tee -a "$poc_stage/activation.log") 2>&1
/usr/bin/date --utc --iso-8601=seconds
restore_poc_api() {
    trap - ERR
    local failed=0
    # Stop while the unit is still installed; systemd also kills its workers.
    /usr/bin/systemctl stop seaparser-poc-api.service || true
    /usr/bin/python3 -B -m deployment.poc_api restore "$poc_stage" || failed=1
    /usr/bin/systemctl daemon-reload || failed=1
    /usr/sbin/apache2ctl configtest && /usr/bin/systemctl reload apache2 || failed=1
    /usr/bin/curl --fail --silent --show-error --max-time 15 http://127.0.0.1:8765/api/health || failed=1
    if /usr/bin/python3 -B -m deployment.poc_api verify-restored "$poc_stage"; then
        if (( !failed )); then /usr/bin/cp "$poc_stage/restoration-check.json" "$poc_stage/rollback-success.json"; fi
    else failed=1; fi
    if (( failed )); then /usr/bin/printf '%s\n' 'ROLLBACK_INCOMPLETE: inspect activation.log; no completed rollback is claimed.' >&2; fi
    return "$failed"
}
activation_failed() {
    local original="$?"
    restore_poc_api || /usr/bin/printf '%s\n' 'Rollback verification failed.' >&2
    exit "$original"
}
if [[ "${1:-}" == --rollback ]]; then restore_poc_api; exit; fi
/usr/bin/python3 -B -m deployment.poc_api verify "$poc_stage"
/usr/bin/systemctl daemon-reload
/usr/bin/python3 -B -m deployment.poc_api verify-restored "$poc_stage"
/usr/bin/systemctl is-active --quiet seaparser-api.service
/usr/bin/test -z "$(/usr/bin/ss -H -ltn 'sport = :8766')"
legacy_pid="$(/usr/bin/systemctl show seaparser-api.service --property=MainPID --value)"
/usr/sbin/apache2ctl configtest
/usr/bin/python3 -B -m deployment.poc_api preflight "$poc_stage"
trap activation_failed ERR
/usr/bin/python3 -B -m deployment.poc_api install "$poc_stage"
/usr/bin/systemctl daemon-reload
/usr/bin/systemctl start seaparser-poc-api.service
/usr/bin/curl --fail --silent --show-error --retry 10 --retry-connrefused --retry-delay 1 'http://127.0.0.1:8766/api/scene?profile=vinga-poc' --output "$poc_stage/active-scene.json"
/usr/sbin/apache2ctl configtest
/usr/bin/systemctl reload apache2
/usr/sbin/runuser -u seaparser -- /usr/bin/env SEAPARSER_POC_URL=https://seaparser.com SEAPARSER_COASTAL_PUBLIC_TEST=1 /usr/bin/node --test --test-concurrency=1 /tmp/seaparser-real-map-data/frontend/tests/poc-live.test.mjs
/usr/bin/test "$legacy_pid" = "$(/usr/bin/systemctl show seaparser-api.service --property=MainPID --value)"
/usr/bin/python3 - "$poc_stage" <<'PY'
import json,sys,datetime
from pathlib import Path
s=Path(sys.argv[1]);m=json.loads((s/'manifest.json').read_text());(s/'activation-success.json').write_text(json.dumps(dict(commit=m['commit'],https_flow='passed',url='https://seaparser.com/poc/',legacy_service_preserved=True,completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat()),indent=2)+'\n')
PY
trap - ERR
/usr/bin/printf '%s\n' 'PoC API activated; public map-click/API/routes/GPX passed. Legacy API and previous public files retained.'
