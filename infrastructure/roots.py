"""Per-root configuration for the autonomous runner.

Two roots are supported:
  app      - SeaParser code (~/app), hashed lockfile, scripts.check
  autonomy - autonomy scripts (~/autonomy), flat layout, bash -n + unittest

Each root has its own task file, run history, report pattern and
verification commands. Worktrees for both roots live under
/home/web/seaparser/worktrees with distinct prefixes so they never collide.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RootConfig:
    name: str
    root: Path
    worktrees_root: Path
    worktree_prefix: str
    branch_prefix: str
    task_file: Path
    history_file: Path
    report_pattern: str
    rules_file: Path
    allowed_prefixes: tuple[str, ...]
    forbidden_files: frozenset[str]
    verify_cmd: str
    fast_verify_cmd: str | None
    max_iterations: int
    max_tool_rounds: int
    max_api_calls: int
    max_tokens_flash: int
    max_tokens_pro: int

    def worktree_path(self, date: str, run: int) -> Path:
        """Return the worktree path for the given date and run."""
        return self.worktrees_root / f"{self.worktree_prefix}-{date}_{run}"

    def branch_name(self, date: str, run: int) -> str:
        """Return the branch name for the given date and run."""
        return f"{self.branch_prefix}-{date}_{run}"

    def report_path(self, date: str, run: int) -> Path:
        """Return the report file path for the given date and run."""
        return self.root / self.report_pattern.format(date=date, run=run)


APP_ROOT = Path("/home/web/seaparser/app")
AUTONOMY_ROOT = Path("/home/web/seaparser/autonomy")
WORKTREES_ROOT = Path("/home/web/seaparser/worktrees")


ROOTS: dict[str, RootConfig] = {
    "app": RootConfig(
        name="app",
        root=APP_ROOT,
        worktrees_root=WORKTREES_ROOT,
        worktree_prefix="run",
        branch_prefix="development/run",
        task_file=APP_ROOT / "AUTONOMOUS_TASK.md",
        history_file=APP_ROOT / "RUN_HISTORY.json",
        report_pattern="RUN_REPORT_{date}_{run}.md",
        rules_file=APP_ROOT / "AGENTS.md",
        allowed_prefixes=("application/", "tests/", "docs/", "scripts/", "infrastructure/"),
        forbidden_files=frozenset({"pyproject.toml", "requirements.lock", "AGENTS.md",
                                   ".tmp_*", "*.tmp", "*.bak", "*~"}),
        verify_cmd="python3 -B -m scripts.check",
        fast_verify_cmd="python3 -B -m unittest tests.test_deepseek_review -v",
        max_iterations=8,
        max_tool_rounds=10,
        max_api_calls=40,
        max_tokens_flash=8000,
        max_tokens_pro=16000,
    ),
    "autonomy": RootConfig(
        name="autonomy",
        root=AUTONOMY_ROOT,
        worktrees_root=WORKTREES_ROOT,
        worktree_prefix="run-autonomy",
        branch_prefix="autonomy-run",
        task_file=AUTONOMY_ROOT / "AUTONOMOUS_TASK.md",
        history_file=AUTONOMY_ROOT / "RUN_HISTORY.json",
        report_pattern="RUN_REPORT_{date}_{run}.md",
        rules_file=AUTONOMY_ROOT / "README.md",
        allowed_prefixes=("",),
        forbidden_files=frozenset({
            "handoff.session", "run.lock", "ssh-probe-launch.lock",
            "work-launch.lock", "tmux.sock", "runner.pid",
            ".tmp_*", "*.tmp", "*.bak", "*~",
            "splice_*.py", "patch_*.py", "fix_*.py",
        }),
        verify_cmd=(
            "set -o pipefail; "
            "bash -n run.sh rotate-logs.sh update-status.sh start-probe.sh start-work.sh stop-work.sh"
            " && python3 -B -m unittest test_capacity_retry test_autonomy_conf 2>&1 | tail -20"
            " && python3 -c \"import ast; [ast.parse(open(f).read()) for f in"
            " ['work_session.py','ssh_probe.py','test_capacity_retry.py','test_autonomy_conf.py']]; print('ast ok')\""
        ),
        fast_verify_cmd=None,
        max_iterations=6,
        max_tool_rounds=12,
        max_api_calls=60,
        max_tokens_flash=8000,
        max_tokens_pro=16000,
    ),
}


def get_root_config(name: str) -> RootConfig:
    """Return the RootConfig for name; raise SystemExit if the root is unknown."""
    if name not in ROOTS:
        raise SystemExit(f"Unknown root: {name!r}. Choose one of: {', '.join(ROOTS)}")
    return ROOTS[name]
