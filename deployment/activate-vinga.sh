#!/bin/bash
# Approved Vinga upgrade. Existing Apache/TLS configuration remains byte-identical.
set -euo pipefail
/usr/bin/test "$(/usr/bin/id -u)" -eq 0
vinga_stage="${1:?Absolute prepared stage required}"
cd /home/web/seaparser/worktrees/real-map-data
/usr/bin/python3 deployment/prepare_vinga.py --verify "$vinga_stage"
source /home/web/seaparser/worktrees/real-map-data/deployment/activation-preflight.sh
require_owned_or_missing "$vinga_stage/unit-before.service" /etc/systemd/system/seaparser-api.service
/usr/sbin/apache2ctl configtest
/usr/bin/systemctl is-active --quiet seaparser-api.service
/usr/bin/curl --fail --silent --show-error http://127.0.0.1:8765/api/health
/usr/bin/python3 /home/web/seaparser/worktrees/real-map-data/deployment/vinga_upgrade.py preflight "$vinga_stage"
/usr/bin/python3 /home/web/seaparser/worktrees/real-map-data/deployment/vinga_upgrade.py backup "$vinga_stage"

restore_vinga() {
    trap - ERR
    /usr/bin/python3 /home/web/seaparser/worktrees/real-map-data/deployment/vinga_upgrade.py restore "$vinga_stage"
    /usr/bin/systemctl daemon-reload
    /usr/bin/systemctl restart seaparser-api.service
    /usr/bin/systemctl is-active --quiet seaparser-api.service
    /usr/bin/curl --fail --silent --show-error --retry 10 --retry-connrefused --retry-delay 1 http://127.0.0.1:8765/api/health
    /usr/bin/printf '%s\n' 'Vinga-publicering avbruten; tidigare tjänst och alla tidigare publika filer återställda.'
}
trap restore_vinga ERR
/usr/bin/python3 /home/web/seaparser/worktrees/real-map-data/deployment/vinga_upgrade.py install "$vinga_stage"
/usr/bin/systemctl daemon-reload
/usr/bin/systemctl restart seaparser-api.service
/usr/bin/systemctl is-active --quiet seaparser-api.service
/usr/bin/curl --fail --silent --show-error --retry 10 --retry-connrefused --retry-delay 1 http://127.0.0.1:8765/api/health
/usr/sbin/runuser -u seaparser -- /usr/bin/python3 /home/web/seaparser/worktrees/real-map-data/deployment/vinga_upgrade.py publish "$vinga_stage"
/usr/sbin/apache2ctl configtest
# No Apache reload needed: proxy, vhost, Directory blocks and TLS are unchanged.
/usr/sbin/runuser -u seaparser -- /usr/bin/env SEAPARSER_DEMO_URL=https://seaparser.com SEAPARSER_DEMO_PROFILE=vinga /usr/bin/node --test /home/web/seaparser/worktrees/real-map-data/frontend/tests/map.test.mjs
/usr/bin/python3 /home/web/seaparser/worktrees/real-map-data/deployment/vinga_upgrade.py verify-public "$vinga_stage"
trap - ERR
/usr/bin/printf '%s\n' 'Vinga publicerad och HTTPS-flödet verifierat. Syntetiskt väder; tidigare demo: /synthetic.html.'
