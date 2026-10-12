#!/bin/bash
# Explicit root rollback. Restores byte content; no chmod/chown/TLS/DB changes.
set -euo pipefail
/usr/bin/test "$(/usr/bin/id -u)" -eq 0
activation_backup=/home/web/seaparser/backups/activation-20261012-c6b0b4f
/usr/bin/test -f "$activation_backup/apache-before.conf"
/usr/bin/test -f "$activation_backup/public-before/index.html"
/usr/bin/cp "$activation_backup/apache-before.conf" /etc/apache2/sites-available/seaparser.conf
/usr/sbin/apache2ctl configtest
/usr/bin/systemctl reload apache2
/usr/bin/cp "$activation_backup/public-before/index.html" /home/web/seaparser/public/index.html
/usr/bin/systemctl disable --now seaparser-api.service
/usr/bin/sha256sum --check "$activation_backup/originals.sha256"
# Unreferenced public resources, module enables and inactive installed files remain.
# They are intentionally not deleted or disabled globally on this shared Apache.
