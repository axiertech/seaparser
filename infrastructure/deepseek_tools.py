"""Tool definitions for DeepSeek Tool Calls. Infrastructure layer only."""
from __future__ import annotations

import difflib
import fnmatch
import json
import subprocess
from pathlib import Path

ALLOWED_COMMANDS = (
    "python", "python3", "pytest", "git status", "git diff", "git log",
    "ls", "cat", "head", "tail", "grep", "find", "bash -n", "wc",
)

FORBIDDEN_SHELL_CHARS = (";", "&&", "||", "|", ">", "<", "`", "$(", "\\", "\n")

DEFAULT_FORBIDDEN = frozenset({"AGENTS.md", "pyproject.toml", "requirements.lock"})

TEMP_PATTERNS = (".tmp_*", "*.tmp", "*.bak", "*~", ".DS_Store")

WRITE_FILE_SIZE_LIMIT = 5000

FUZZY_THRESHOLD = 0.85


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file inside the worktree.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path, e.g. application/foo.py"}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Create a new file, or fully rewrite a small file (under 5000 bytes). "
                "For existing larger files, use edit_file instead - write_file will "
                "return an error asking you to switch."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path, e.g. scripts/new.py"},
                    "content": {"type": "string", "description": "Full file content"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": (
                "Edit an existing file by replacing a block of text. Tries exact "
                "string match first; if not found, falls back to fuzzy line-level "
                "matching that tolerates whitespace/indent differences. Use this "
                "for small changes to large files instead of write_file. The "
                "old_string must identify a unique block - if it appears more "
                "than once, add more surrounding context."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path"},
                    "old_string": {"type": "string", "description": "Text to find (unique or near-unique)"},
                    "new_string": {"type": "string", "description": "Replacement text"},
                },
                "required": ["path", "old_string", "new_string"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run an allowed shell command in the worktree and return output.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Command, e.g. 'python -m pytest tests/'"}
                },
                "required": ["command"],
            },
        },
    },
]


def _validate_path(worktree: Path, rel: str) -> Path:
    """Resolve a relative path and reject escapes from the worktree."""
    target = (worktree / rel).resolve()
    if worktree.resolve() not in target.parents and target != worktree.resolve():
        raise ValueError(f"Path outside worktree: {rel}")
    return target


def _validate_command(cmd: str) -> str | None:
    """Return an error message if the command is not allowed, else None."""
    if any(ch in cmd for ch in FORBIDDEN_SHELL_CHARS):
        return f"Command contains forbidden shell characters: {cmd!r}"
    if not any(cmd == p or cmd.startswith(p + " ") for p in ALLOWED_COMMANDS):
        return f"Command is not allowed: {cmd!r}"
    return None


def _is_forbidden(name: str, forbidden: frozenset[str]) -> bool:
    """Return True if name matches any exact entry or glob pattern."""
    for pattern in forbidden:
        if "*" in pattern or "?" in pattern:
            if fnmatch.fnmatch(name, pattern):
                return True
        elif name == pattern:
            return True
    return False


def _find_fuzzy_match(text: str, old_string: str,
                      threshold: float = FUZZY_THRESHOLD) -> tuple[int, int, float] | None:
    """Find an approximate line range in text matching old_string.

    Uses line-level difflib.SequenceMatcher with whitespace normalization.
    Blanks and indent differences are tolerated: only non-blank lines are
    compared, and for each start position the window grows forward until
    enough non-blank content has been collected. Returns (start_line,
    end_line_exclusive, similarity) or None if no match above threshold.
    Ambiguous matches (two regions with similar scores) are rejected so a
    wrong block is not replaced.
    """
    text_lines = text.split("\n")
    old_lines = [l for l in old_string.split("\n") if l.strip()]

    if not old_lines or len(old_lines) > len(text_lines):
        return None

    n = len(old_lines)
    old_normalized = "\n".join(l.strip() for l in old_lines)

    scored: list[tuple[float, int, int]] = []
    for start in range(len(text_lines)):
        window_lines: list[str] = []
        end = start
        while end < len(text_lines) and len(window_lines) < n:
            if text_lines[end].strip():
                window_lines.append(text_lines[end])
            end += 1
        if len(window_lines) < n:
            continue
        window_normalized = "\n".join(l.strip() for l in window_lines)
        ratio = difflib.SequenceMatcher(None, old_normalized, window_normalized,
                                        autojunk=False).ratio()
        if ratio >= threshold:
            scored.append((ratio, start, end))

    if not scored:
        return None

    scored.sort(key=lambda x: (-x[0], x[1]))
    best_ratio, best_start, best_end = scored[0]

    if len(scored) > 1:
        second_ratio, second_start, _ = scored[1]
        if (best_ratio - second_ratio) < 0.05 and abs(best_start - second_start) > n:
            return None  # ambiguous

    return (best_start, best_end, best_ratio)


def _edit_file_exact(text: str, old_string: str, new_string: str) -> tuple[str, str] | str:
    """Try exact replacement. Return (new_text, message) or an error string."""
    count = text.count(old_string)
    if count == 0:
        return "no_exact_match"
    if count > 1:
        return (f"ERROR: old_string matches {count} times. "
                f"Provide more surrounding context to make it unique.")
    return (text.replace(old_string, new_string, 1),
            f"exact match, {len(old_string)} -> {len(new_string)} chars")


def _edit_file_fuzzy(text: str, old_string: str, new_string: str) -> tuple[str, str] | None:
    """Try fuzzy replacement. Return (new_text, message) or None if no match."""
    match = _find_fuzzy_match(text, old_string)
    if match is None:
        return None

    start_line, end_line, ratio = match
    text_lines = text.split("\n")
    new_lines = new_string.split("\n")
    result = "\n".join(text_lines[:start_line] + new_lines + text_lines[end_line:])
    return (result,
            f"fuzzy match (similarity {ratio:.2f}): "
            f"replaced lines {start_line + 1}-{end_line} with {len(new_lines)} new lines")


def execute_tool(worktree: Path, name: str, arguments: str,
                 forbidden_files: frozenset[str] | None = None) -> str:
    """Execute a tool call and return its result as a string."""
    args = json.loads(arguments)
    forbidden = forbidden_files if forbidden_files is not None else DEFAULT_FORBIDDEN

    if name == "read_file":
        target = _validate_path(worktree, args["path"])
        if not target.exists():
            return f"File does not exist: {args['path']}"
        return target.read_text()

    if name == "write_file":
        target = _validate_path(worktree, args["path"])
        if _is_forbidden(target.name, forbidden):
            raise ValueError(f"Forbidden file: {args['path']}")
        if target.exists() and target.stat().st_size > WRITE_FILE_SIZE_LIMIT:
            return (f"ERROR: {args['path']} is {target.stat().st_size} bytes, "
                    f"above the {WRITE_FILE_SIZE_LIMIT}-byte write_file limit. "
                    f"Use edit_file for small changes instead of rewriting the "
                    f"whole file.")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(args["content"])
        return f"Wrote {args['path']} ({len(args['content'])} chars)"

    if name == "edit_file":
        target = _validate_path(worktree, args["path"])
        if _is_forbidden(target.name, forbidden):
            raise ValueError(f"Forbidden file: {args['path']}")
        if not target.exists():
            return (f"ERROR: {args['path']} does not exist. "
                    f"Use write_file to create new files.")
        text = target.read_text()
        old_string = args["old_string"]
        new_string = args["new_string"]

        if not old_string:
            return "ERROR: old_string is empty."

        result = _edit_file_exact(text, old_string, new_string)
        if isinstance(result, tuple):
            new_text, message = result
            target.write_text(new_text)
            return f"Edited {args['path']}: {message}"
        if isinstance(result, str) and result != "no_exact_match":
            return result

        fuzzy = _edit_file_fuzzy(text, old_string, new_string)
        if fuzzy is not None:
            new_text, message = fuzzy
            target.write_text(new_text)
            return f"Edited {args['path']}: {message}"

        return (f"ERROR: old_string not found in {args['path']} "
                f"(exact and fuzzy both failed). Read the file to see the exact "
                f"content, or provide 2-3 lines of surrounding context so the "
                f"match is unique.")

    if name == "run_command":
        cmd = args["command"]
        error = _validate_command(cmd)
        if error:
            return error
        proc = subprocess.run(
            cmd, shell=True, cwd=worktree, capture_output=True, text=True, timeout=120,
        )
        output = (proc.stdout + proc.stderr)[-4000:]
        return f"exit={proc.returncode}\n{output}"

    return f"Unknown tool: {name}"


def clean_temp_files(worktree: Path) -> list[str]:
    """Remove temp files matching TEMP_PATTERNS. Return relative paths removed."""
    removed: list[str] = []
    for pattern in TEMP_PATTERNS:
        for path in worktree.rglob(pattern):
            if path.is_file():
                try:
                    removed.append(str(path.relative_to(worktree)))
                    path.unlink()
                except OSError:
                    pass
    return removed
