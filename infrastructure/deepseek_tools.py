"""Tool definitions for DeepSeek Tool Calls. Infrastructure layer only."""
from __future__ import annotations

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
            "description": "Write content to a file inside the worktree. Creates the file if it does not exist.",
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
            "description": "Edit an existing file by replacing an exact substring. Use this for small changes to large files instead of write_file (which requires the full new content).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path"},
                    "old_string": {"type": "string", "description": "Exact text to find (must be unique in the file)"},
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
        if target.exists() and target.stat().st_size > 5000:
            return (f"ERROR: {args['path']} is {target.stat().st_size} bytes. "
                    f"Use edit_file for small changes instead of rewriting "
                    f"the whole file with write_file.")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(args["content"])
        return f"Wrote {args['path']} ({len(args['content'])} chars)"

    if name == "edit_file":
        target = _validate_path(worktree, args["path"])
        if _is_forbidden(target.name, forbidden):
            raise ValueError(f"Forbidden file: {args['path']}")
        if not target.exists():
            return f"ERROR: {args['path']} does not exist. Use write_file to create new files."
        old_string = args["old_string"]
        new_string = args["new_string"]
        text = target.read_text()
        count = text.count(old_string)
        if count == 0:
            return (f"ERROR: old_string not found in {args['path']}. "
                    f"Read the file first to see the exact content.")
        if count > 1:
            return (f"ERROR: old_string matches {count} times in {args['path']}. "
                    f"Provide a longer unique string.")
        target.write_text(text.replace(old_string, new_string, 1))
        return f"Edited {args['path']}: {len(old_string)} chars replaced with {len(new_string)} chars"

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
