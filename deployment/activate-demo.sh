#!/bin/bash
# Run explicitly as root only after reviewing the documented approved activation.
set -euo pipefail
/usr/bin/test "$(/usr/bin/id -u)" -eq 0
activation_backup=/home/web/seaparser/backups/activation-20261012-c6b0b4f
/usr/bin/test -f "$activation_backup/manifest.json"
/usr/bin/test ! -e /etc/systemd/system/seaparser-api.service
/usr/bin/test ! -e /etc/apache2/seaparser-api.conf
/usr/bin/test -z "$(/usr/bin/ss -H -ltn 'sport = :8765')"
/usr/bin/sha256sum --check "$activation_backup/originals.sha256"
/usr/sbin/apache2ctl configtest

rollback_activation() {
    trap - ERR
    /usr/bin/cp "$activation_backup/apache-before.conf" /etc/apache2/sites-available/seaparser.conf
    /usr/bin/cp "$activation_backup/public-before/index.html" /home/web/seaparser/public/index.html
    /usr/bin/systemctl disable --now seaparser-api.service || true
    if /usr/sbin/apache2ctl configtest; then
        /usr/bin/systemctl reload apache2
    fi
    /usr/bin/printf '%s\n' 'Aktiveringen avbröts. Apache och index återställda; API stoppat.'
}
trap rollback_activation ERR

# Modules are currently absent. Enable only those needed for the approved proxy.
/usr/sbin/a2enmod proxy proxy_http
/usr/bin/cp "$activation_backup/apache-api.conf" /etc/apache2/seaparser-api.conf
/usr/bin/cp "$activation_backup/apache-ready.conf" /etc/apache2/sites-available/seaparser.conf
/usr/bin/cp "$activation_backup/seaparser-api.service" /etc/systemd/system/seaparser-api.service
/usr/sbin/apache2ctl configtest
/usr/bin/systemctl daemon-reload
/usr/bin/systemctl enable --now seaparser-api.service
/usr/bin/systemctl is-active --quiet seaparser-api.service
/usr/bin/curl --fail --silent --show-error --retry 10 --retry-connrefused --retry-delay 1 http://127.0.0.1:8765/api/health
/usr/sbin/apache2ctl configtest
/usr/bin/systemctl reload apache2
/usr/bin/curl --fail --silent --show-error https://seaparser.com/api/health

# Resources already published by seaparser; replace only the existing index last.
/usr/bin/cp "$activation_backup/frontend-ready/index.html" /home/web/seaparser/public/index.html
/usr/sbin/runuser -u seaparser -- /usr/bin/env SEAPARSER_DEMO_URL=https://seaparser.com /usr/bin/node --test /home/web/seaparser/app/frontend/tests/map.test.mjs
trap - ERR
/usr/bin/printf '%s\n' 'Aktivering och publik HTTP/DOM-verifiering lyckades.'
