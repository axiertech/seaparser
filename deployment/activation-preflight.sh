# Read-only deployment identity check. Source this file; do not bypass mismatches.
require_owned_or_missing() {
    local expected_file="$1" installed_file="$2"
    if ! /usr/bin/test -f "$expected_file" || /usr/bin/test -L "$expected_file"; then
        /usr/bin/printf '%s\n' "Stoppar: verifierat källunderlag saknas: $expected_file" >&2
        return 1
    fi
    if /usr/bin/test -e "$installed_file" || /usr/bin/test -L "$installed_file"; then
        if ! /usr/bin/test -f "$installed_file" || /usr/bin/test -L "$installed_file" || ! /usr/bin/cmp --silent "$expected_file" "$installed_file"; then
            /usr/bin/printf '%s\n' "Stoppar: filen tillhör inte verifierad deployment: $installed_file" >&2
            return 1
        fi
    fi
}
