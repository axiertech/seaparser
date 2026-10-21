"""Verktygsdefinitioner för DeepSeek Tool Calls. Endast infrastruktur."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

# Vitlista för kommandon som får köras i worktreen
ALLOWED_COMMANDS = (
    "python", "python3", "pytest", "git status", "git diff", "git log",
    "ls", "cat", "head", "tail", "grep", "find",
)

FORBIDDEN_FILES = {"AGENTS.md", "pyproject.toml", "requirements.lock"}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Läs en fils innehåll i worktreen.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relativ sökväg, t.ex. application/foo.py"}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Skriv innehåll till en fil i worktreen. Skapar filen om den inte finns.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relativ sökväg, t.ex. scripts/nytt.py"},
                    "content": {"type": "string", "description": "Fullständigt filinnehåll"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Kör ett tillåtet shell-kommando i worktreen och returnera output.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Kommandot, t.ex. 'python -m pytest tests/'"}
                },
                "required": ["command"],
            },
        },
    },
]


def _validate_path(worktree: Path, rel: str) -> Path:
    """Säkerställ att sökvägen ligger inom worktreen."""
    target = (worktree / rel).resolve()
    if worktree.resolve() not in target.parents and target != worktree.resolve():
        raise ValueError(f"Sökväg utanför worktree: {rel}")
    return target


def execute_tool(worktree: Path, name: str, arguments: str) -> str:
    """Utför ett verktygsanrop och returnera resultatet som sträng."""
    args = json.loads(arguments)

    if name == "read_file":
        target = _validate_path(worktree, args["path"])
        if not target.exists():
            return f"Filen finns inte: {args['path']}"
        return target.read_text()

    if name == "write_file":
        target = _validate_path(worktree, args["path"])
        if target.name in FORBIDDEN_FILES:
            raise ValueError(f"Otillåten fil: {args['path']}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(args["content"])
        return f"Skrev {args['path']} ({len(args['content'])} tecken)"

    if name == "run_command":
        cmd = args["command"]
        if not any(cmd.startswith(prefix) for prefix in ALLOWED_COMMANDS):
            return f"Kommandot är inte tillåtet: {cmd}"
        proc = subprocess.run(
            cmd, shell=True, cwd=worktree, capture_output=True, text=True, timeout=60,
        )
        output = (proc.stdout + proc.stderr)[-4000:]
        return f"exit={proc.returncode}\n{output}"

    return f"Okänt verktyg: {name}"
