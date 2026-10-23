"""Task safety, scope enforcement and sanity checks.

This module owns the rules that protect the codebase from an autonomous
agent. It is pure: no API calls, no network, no subprocesses.
"""
from __future__ import annotations

import re

from infrastructure.roots import RootConfig


def allowed_files_for_task(task_text: str) -> frozenset[str] | None:
    """Parse 'Allowed files:' from AUTONOMOUS_TASK.md.

    Supports both inline form and markdown header + bullet list:
        Allowed files: a, b, c
        ## Allowed files:
        - a
        - b

    Returns None when the section is absent (no restriction), or a
    frozenset of relative paths that may be created or modified.
    """
    lines = task_text.splitlines()
    paths: set[str] = set()
    found = False
    i = 0
    while i < len(lines):
        stripped = lines[i].lstrip("# ").rstrip()
        if stripped.lower().startswith("allowed files:"):
            found = True
            rest = stripped.split(":", 1)[1].strip()
            if rest:
                for part in rest.split(","):
                    part = part.strip()
                    if part:
                        paths.add(part)
            j = i + 1
            while j < len(lines):
                nxt = lines[j].strip()
                if not nxt:
                    j += 1
                    continue
                if nxt[:1] in "-*+":
                    item = nxt[1:].strip()
                    if item:
                        paths.add(item)
                    j += 1
                else:
                    break
            i = j - 1
        i += 1
    if not found:
        return None
    return frozenset(paths) if paths else None


def sanity_check_task(config: RootConfig, task_text: str) -> bool:
    """Check 'Allowed files:' against the base tree and prefix rules.

    Returns True if the task is safe to start, False if there are
    fatal errors. Warnings (e.g. missing files that might be created
    by the task) are printed but do not fail the check.
    """
    allowed = allowed_files_for_task(task_text)
    if allowed is None:
        print("INFO: No 'Allowed files:' line. The agent may modify any file.")
        return True

    missing = []
    outside_prefix = []
    task_lower = task_text.lower()
    
    # Om uppgiften innehåller "create", "new" eller "add" antar vi att
    # det är OK att filer saknas (de ska skapas).
    allow_creation = any(word in task_lower for word in ["create", "new file", "add a new", "skapa"])

    for f in allowed:
        if f.endswith("/"):
            # Det är en mapp, vi kräver inte att den finns (kan skapas)
            continue
        if not (config.root / f).exists():
            if allow_creation:
                print(f"INFO: '{f}' saknas i basen men uppgiften tillåter skapande.")
            else:
                missing.append(f)
                
        # Check if it's outside the allowed prefixes
        if not any(f.startswith(p) for p in config.allowed_prefixes):
            outside_prefix.append(f)

    ok = True

    if outside_prefix:
        print(f"WARNING: Allowed files outside standard prefixes: {', '.join(outside_prefix)}")
        print(f"  (Standard prefixes: {', '.join(config.allowed_prefixes)})")
        # Vi gör detta till ett fel om filen inte finns alls, annars bara en varning
        if missing:
            ok = False

    if missing:
        print(f"ERROR: Allowed files do not exist in the base tree: {', '.join(missing)}")
        print("  If the task is NOT creating these files, you probably have a typo.")
        ok = False

    return ok


def check_scope(written: list[str], allowed: frozenset[str] | None) -> str | None:
    """Return an error message if written files exceed the allowlist, else None.

    Allowed entries can be exact paths (e.g. 'application/planning.py')
    or directory prefixes ending with '/' (e.g. 'frontend/map/'), which
    match any file under that directory. This lets the user write
    'frontend/map/' without knowing the exact filenames.
    """
    if allowed is None:
        return None

    extra = []
    for f in written:
        if f in allowed:
            continue
        if any(f.startswith(prefix) for prefix in allowed if prefix.endswith("/")):
            continue
        extra.append(f)

    if not extra:
        return None
    return (
        f"SCOPE VIOLATION: modified files not in the allowed list: "
        f"{', '.join(sorted(extra))}. The task allows only: "
        f"{', '.join(sorted(allowed))}. "
        f"Revert each extra file with 'git checkout -- <path>' and do "
        f"NOT try to fix it. Stay within the allowlist on the next try."
    )
