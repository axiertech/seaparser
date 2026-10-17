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
restore_poc_api() {
    trap - ERR
    /usr/bin/python3 -B -m deployment.poc_api restore "$poc_stage"
    /usr/bin/systemctl stop seaparser-poc-api.service || true
    /usr/bin/systemctl daemon-reload
    /usr/sbin/apache2ctl configtest
    /usr/bin/systemctl reload apache2
    /usr/bin/curl --fail --silent --show-error http://127.0.0.1:8765/api/health
}
if [[ "${1:-}" == --rollback ]]; then restore_poc_api; exit; fi
/usr/bin/python3 -B -m deployment.poc_api verify "$poc_stage"
/usr/bin/systemctl is-active --quiet seaparser-api.service
/usr/bin/test -z "$(/usr/bin/ss -H -ltn 'sport = :8766')"
legacy_pid="$(/usr/bin/systemctl show seaparser-api.service --property=MainPID --value)"
/usr/sbin/apache2ctl configtest
trap restore_poc_api ERR
/usr/bin/python3 -B -m deployment.poc_api install "$poc_stage"
/usr/bin/systemctl daemon-reload
/usr/bin/systemctl start seaparser-poc-api.service
/usr/bin/curl --fail --silent --show-error --retry 10 --retry-connrefused --retry-delay 1 'http://127.0.0.1:8766/api/scene?profile=vinga-poc' --output "$poc_stage/active-scene.json"
/usr/sbin/apache2ctl configtest
/usr/bin/systemctl reload apache2
/usr/sbin/runuser -u seaparser -- /usr/bin/env SEAPARSER_POC_URL=https://seaparser.com /usr/bin/node --test /tmp/seaparser-real-map-data/frontend/tests/poc-live.test.mjs
/usr/bin/test "$legacy_pid" = "$(/usr/bin/systemctl show seaparser-api.service --property=MainPID --value)"
/usr/bin/python3 - "$poc_stage" <<'PY'
import json,sys,datetime
from pathlib import Path
s=Path(sys.argv[1]);m=json.loads((s/'manifest.json').read_text());(s/'activation-success.json').write_text(json.dumps(dict(commit=m['commit'],https_flow='passed',url='https://seaparser.com/poc/',legacy_service_preserved=True,completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat()),indent=2)+'\n')
PY
trap - ERR
/usr/bin/printf '%s\n' 'PoC API activated; public map-click/API/routes/GPX passed. Legacy API and previous public files retained.'
