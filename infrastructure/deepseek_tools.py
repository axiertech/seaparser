"""Tool definitions for DeepSeek Tool Calls. Infrastructure layer only."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ALLOWED_COMMANDS = (
    "python", "python3", "pytest", "git status", "git diff", "git log",
    "ls", "cat", "head", "tail", "grep", "find", "bash -n", "wc",
)

FORBIDDEN_SHELL_CHARS = (";", "&&", "||", "|", ">", "<", "`", "$(", "\\", "\n")

FORBIDDEN_FILES = {"AGENTS.md", "pyproject.toml", "requirements.lock"}

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


def execute_tool(worktree: Path, name: str, arguments: str,
                 forbidden_files: frozenset[str] | None = None) -> str:
    args = json.loads(arguments)
    forbidden = forbidden_files if forbidden_files is not None else FORBIDDEN_FILES

    if name == "read_file":
        target = _validate_path(worktree, args["path"])
        if not target.exists():
            return f"File does not exist: {args['path']}"
        return target.read_text()

    if name == "write_file":
        target = _validate_path(worktree, args["path"])
        if target.name in forbidden:
            raise ValueError(f"Forbidden file: {args['path']}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(args["content"])
        return f"Wrote {args['path']} ({len(args['content'])} chars)"

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
