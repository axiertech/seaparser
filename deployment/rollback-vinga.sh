#!/bin/bash
set -euo pipefail
/usr/bin/test "$(/usr/bin/id -u)" -eq 0
vinga_stage="${1:?Absolute prepared stage required}"
cd /tmp/seaparser-real-map-data
/usr/bin/python3 /tmp/seaparser-real-map-data/deployment/vinga_upgrade.py restore "$vinga_stage"
/usr/bin/systemctl daemon-reload
/usr/bin/systemctl restart seaparser-api.service
/usr/sbin/apache2ctl configtest
/usr/bin/systemctl is-active --quiet seaparser-api.service
/usr/bin/curl --fail --silent --show-error --retry 10 --retry-connrefused --retry-delay 1 http://127.0.0.1:8765/api/health
