"""Verify and merge a completed autonomous run.

Usage:  python -B -m scripts.verify_run [--root app|autonomy] <run> [--dry-run] [--no-cleanup] [--fast]

<run> is either "3" (today's run number) or "2026-10-21_3".

Steps (stops on first failure):
  1. Look up run in <root>/RUN_HISTORY.json
  2. Check that the worktree exists
  3. Run the fast verify in the worktree
  4. Run the full verify in the worktree (unless --fast)
  5. Check that the worktree is clean (git status)
  6. Check that HEAD matches the commit in the history
  7. Merge into the current branch (unless --dry-run)
  8. Run the full verify in <root> after merge
  9. Clean up the worktree (unless --dry-run / --no-cleanup)

Never pushes. Never merges to main. Never mutates RUN_HISTORY.json.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from infrastructure.roots import RootConfig, get_root_config


REPORT_APPEND_MARKER = "\n\n## Verification\n"


@dataclass
class StepResult:
    name: str
    ok: bool
    detail: str = ""


def _load_history(config: RootConfig) -> dict:
    if not config.history_file.exists():
        raise SystemExit(f"Missing {config.history_file}")
    try:
        return json.loads(config.history_file.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid {config.history_file.name}: {exc.msg}") from None


def _resolve_run(history: dict, run_arg: str) -> dict:
    today = dt.date.today().isoformat()
    if "_" in run_arg:
        date, _, num = run_arg.partition("_")
        candidates = [r for r in history["runs"]
                      if r.get("date") == date and str(r.get("run")) == num]
    else:
        candidates = [r for r in history["runs"]
                      if r.get("date") == today and str(r.get("run")) == run_arg]
        if len(candidates) != 1:
            broader = [r for r in history["runs"]
                       if str(r.get("run")) == run_arg]
            if broader:
                candidates = broader
    if not candidates:
        raise SystemExit(f"No run matches {run_arg!r}")
    if len(candidates) > 1:
        raise SystemExit(
            f"Multiple runs match {run_arg!r}: "
            + ", ".join(f"{r['date']}_{r['run']}" for r in candidates)
            + ". Specify the date, e.g. 2026-10-21_3."
        )
    return candidates[0]


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def _run_shell(cmd: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", "-c", cmd], cwd=cwd, capture_output=True, text=True)


def _tail(text: str, lines: int = 30) -> str:
    return "\n".join(text.splitlines()[-lines:])


def _check_completed(entry: dict) -> StepResult:
    if entry.get("status") not in ("completed", "reviewer_unavailable"):
        return StepResult("status", False,
                          f"status={entry.get('status')!r}, "
                          f"expected 'completed' or 'reviewer_unavailable'")
    if not entry.get("commit"):
        return StepResult("commit", False,
                          "commit is null (dry run or failed)")
    return StepResult("register", True,
                      f"run={entry.get('run', '?')} commit={entry['commit'][:10]}")


def _check_worktree(entry: dict) -> StepResult:
    wt = Path(entry.get("worktree", ""))
    if not str(wt) or not wt.exists():
        return StepResult("worktree", False, f"missing: {wt}")
    return StepResult("worktree", True, str(wt))


def _run_fast_verify(config: RootConfig, worktree: Path) -> StepResult:
    if not config.fast_verify_cmd:
        return StepResult("fast verify", True, "no fast command, skipped")
    proc = _run_shell(config.fast_verify_cmd, worktree)
    if proc.returncode != 0:
        return StepResult("fast verify", False, _tail(proc.stdout + proc.stderr))
    return StepResult("fast verify", True, "ok")


def _run_full_verify(config: RootConfig, worktree: Path) -> StepResult:
    proc = _run_shell(config.verify_cmd, worktree)
    if proc.returncode != 0:
        return StepResult("full verify", False, _tail(proc.stdout + proc.stderr))
    return StepResult("full verify", True, "ok")


def _check_clean(worktree: Path) -> StepResult:
    proc = _run(["git", "status", "--porcelain"], cwd=worktree)
    if proc.returncode != 0:
        return StepResult("worktree clean", False, _tail(proc.stderr))
    if proc.stdout.strip():
        return StepResult("worktree clean", False,
                          "uncommitted changes:\n" + proc.stdout)
    return StepResult("worktree clean", True, "no uncommitted changes")


def _check_head(worktree: Path, expected_commit: str) -> StepResult:
    proc = _run(["git", "rev-parse", "HEAD"], cwd=worktree)
    if proc.returncode != 0:
        return StepResult("HEAD", False, _tail(proc.stderr))
    actual = proc.stdout.strip()
    if actual != expected_commit:
        return StepResult("HEAD", False,
                          f"expected {expected_commit[:10]}, got {actual[:10]}")
    return StepResult("HEAD", True, actual[:10])


def _merge(config: RootConfig, branch: str, message: str) -> StepResult:
    proc = _run(["git", "merge", "--no-ff", branch, "-m", message], cwd=config.root)
    if proc.returncode != 0:
        return StepResult("merge", False, _tail(proc.stdout + proc.stderr))
    return StepResult("merge", True, f"merged {branch}")


def _check_after_merge(config: RootConfig) -> StepResult:
    proc = _run_shell(config.verify_cmd, config.root)
    if proc.returncode != 0:
        return StepResult("verify after merge", False, _tail(proc.stdout + proc.stderr))
    return StepResult("verify after merge", True, "ok")


def _cleanup(config: RootConfig, worktree: Path, branch: str) -> StepResult:
    proc = _run(["git", "worktree", "remove", str(worktree)], cwd=config.root)
    if proc.returncode != 0:
        return StepResult("cleanup", False, _tail(proc.stderr))
    proc = _run(["git", "branch", "-D", branch], cwd=config.root)
    if proc.returncode != 0:
        return StepResult("cleanup", False, _tail(proc.stderr))
    return StepResult("cleanup", True, f"removed {worktree} and {branch}")


def _append_report(entry: dict, steps: list[StepResult], overall_ok: bool) -> None:
    report_path = entry.get("report")
    if not report_path:
        return
    report = Path(report_path)
    if not report.exists():
        return
    text = report.read_text()
    if REPORT_APPEND_MARKER in text:
        text = text.split(REPORT_APPEND_MARKER)[0]
    lines = [REPORT_APPEND_MARKER.rstrip(), ""]
    lines.append(f"- Result: {'OK' if overall_ok else 'FAILED'}")
    lines.append(f"- Verified: {dt.datetime.now().astimezone().isoformat(timespec='seconds')}")
    for s in steps:
        marker = "OK" if s.ok else "FAIL"
        first = s.detail.splitlines()[0] if s.detail else ""
        lines.append(f"- [{marker}] {s.name}: {first}")
    report.write_text(text + "\n".join(lines) + "\n")


def _print_step(step: StepResult) -> None:
    marker = "OK" if step.ok else "FAIL"
    first = step.detail.splitlines()[0] if step.detail else ""
    print(f"[{marker}] {step.name}: {first}")
    if not step.ok and step.detail:
        for line in step.detail.splitlines()[1:]:
            print(f"       {line}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Verify and merge a run")
    parser.add_argument("run", help="e.g. 3 or 2026-10-21_3")
    parser.add_argument("--root", default="app", choices=["app", "autonomy"],
                        help="Which project root to verify against")
    parser.add_argument("--dry-run", action="store_true",
                        help="Verify but do not merge or clean up")
    parser.add_argument("--no-cleanup", action="store_true",
                        help="Keep the worktree after merge")
    parser.add_argument("--fast", action="store_true",
                        help="Skip the full verify in the worktree")
    args = parser.parse_args(argv)

    config = get_root_config(args.root)
    history = _load_history(config)
    entry = _resolve_run(history, args.run)
    print(f"Root:   {config.name} ({config.root})")
    print(f"Run:    {entry['date']}_{entry['run']}")
    print(f"Branch: {entry['branch']}")
    print(f"Commit: {entry.get('commit') or '-'}")
    print(f"Status: {entry.get('status')}\n")

    steps: list[StepResult] = []
    overall_ok = True

    def record(step: StepResult) -> bool:
        nonlocal overall_ok
        steps.append(step)
        _print_step(step)
        if not step.ok:
            overall_ok = False
        return step.ok

    if not record(_check_completed(entry)):
        _append_report(entry, steps, overall_ok)
        return 1

    if not record(_check_worktree(entry)):
        _append_report(entry, steps, overall_ok)
        return 1

    worktree = Path(entry["worktree"])

    if not record(_run_fast_verify(config, worktree)):
        _append_report(entry, steps, overall_ok)
        print(f"\nWorktree kept for inspection: {worktree}")
        return 1

    if not args.fast:
        if not record(_run_full_verify(config, worktree)):
            _append_report(entry, steps, overall_ok)
            print(f"\nWorktree kept for inspection: {worktree}")
            return 1

    if not record(_check_clean(worktree)):
        _append_report(entry, steps, overall_ok)
        print(f"\nWorktree kept for inspection: {worktree}")
        return 1

    if not record(_check_head(worktree, entry["commit"])):
        _append_report(entry, steps, overall_ok)
        print(f"\nWorktree kept for inspection: {worktree}")
        return 1

    if args.dry_run:
        print("\n--dry-run: skipping merge and cleanup.")
        _append_report(entry, steps, overall_ok)
        return 0

    merge_msg = (f"Merge autonomous {config.name} run {entry['date']}_{entry['run']}: "
                 f"{entry.get('task_preview', '')[:60]}")
    if not record(_merge(config, entry["branch"], merge_msg)):
        _append_report(entry, steps, overall_ok)
        print("\nMerge failed. Worktree kept.")
        return 1

    if not record(_check_after_merge(config)):
        _append_report(entry, steps, overall_ok)
        print("\nWARNING: merge already applied. Back out with 'git reset --hard ORIG_HEAD'.")
        return 1

    if not args.no_cleanup:
        record(_cleanup(config, worktree, entry["branch"]))

    _append_report(entry, steps, overall_ok)
    print(f"\nSummary: {'OK' if overall_ok else 'FAILED'}")
    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())
