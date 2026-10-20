"""Verifiera och merga en avslutad autonom körning.

Kör manuellt:
  python -B -m scripts.verify_run <run> [--dry-run] [--no-cleanup] [--fast]

<run> är antingen "3" (dagens run) eller "2026-10-20_3".

Flöde (stoppar vid första fel):
  1. Slå upp run i RUN_HISTORY.json
  2. Kontrollera att worktree finns
  3. Kör tester i worktreen
  4. Kör scripts.check i worktreen (eller --fast)
  5. Kontrollera att worktreen är ren (git status)
  6. Kontrollera att HEAD == commit i registret
  7. Merga in i aktuell branch (om inte --dry-run)
  8. Kör scripts.check i ~/app efter merge
  9. Städa worktreen (om inte --dry-run/--no-cleanup)

Pushar aldrig. Mergar aldrig till main. Rör inte RUN_HISTORY.json.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
HISTORY_FILE = APP_ROOT / "RUN_HISTORY.json"
REPORT_APPEND_MARKER = "\n\n## Verifiering\n"


@dataclass
class StepResult:
    name: str
    ok: bool
    detail: str = ""


def _load_history() -> dict:
    if not HISTORY_FILE.exists():
        raise SystemExit(f"Saknar {HISTORY_FILE}")
    try:
        return json.loads(HISTORY_FILE.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Ogiltig RUN_HISTORY.json: {exc.msg}") from None


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
            if len(broader) == 1:
                candidates = broader
            elif len(broader) > 1:
                candidates = broader
    if not candidates:
        raise SystemExit(f"Hittar ingen run som matchar {run_arg!r}")
    if len(candidates) > 1:
        raise SystemExit(
            f"Flera runs matchar {run_arg!r}: "
            + ", ".join(f"{r['date']}_{r['run']}" for r in candidates)
            + ". Ange datum, t.ex. 2026-10-20_3."
        )
    return candidates[0]


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def _tail(text: str, lines: int = 30) -> str:
    return "\n".join(text.splitlines()[-lines:])


def _check_completed(entry: dict) -> StepResult:
    if entry.get("status") != "completed":
        return StepResult("status", False,
                          f"status={entry.get('status')!r}, förväntade 'completed'")
    if not entry.get("commit"):
        return StepResult("commit", False,
                          "commit är null (torrkörning eller misslyckad)")
    run_label = entry.get("run", "?")
    return StepResult("register", True,
                      f"run={run_label} commit={entry['commit'][:10]}")


def _check_worktree(entry: dict) -> StepResult:
    wt = Path(entry.get("worktree", ""))
    if not str(wt) or not wt.exists():
        return StepResult("worktree", False, f"saknas: {wt}")
    return StepResult("worktree", True, str(wt))


def _run_deepseek_tests(worktree: Path) -> StepResult:
    proc = _run([sys.executable, "-B", "-m", "unittest",
                 "tests.test_deepseek_review", "-v"], cwd=worktree)
    if proc.returncode != 0:
        return StepResult("deepseek-tester", False, _tail(proc.stdout + proc.stderr))
    return StepResult("deepseek-tester", True, "8 tester ok")


def _run_full_check(worktree: Path, fast: bool) -> StepResult:
    if fast:
        return _run_deepseek_tests(worktree)
    proc = _run([sys.executable, "-B", "-m", "scripts.check"], cwd=worktree)
    if proc.returncode != 0:
        return StepResult("scripts.check (worktree)", False,
                          _tail(proc.stdout + proc.stderr))
    return StepResult("scripts.check (worktree)", True, "godkänd")


def _check_clean(worktree: Path) -> StepResult:
    proc = _run(["git", "status", "--porcelain"], cwd=worktree)
    if proc.returncode != 0:
        return StepResult("worktree ren", False, _tail(proc.stderr))
    if proc.stdout.strip():
        return StepResult("worktree ren", False,
                          "osparade ändringar:\n" + proc.stdout)
    return StepResult("worktree ren", True, "inga osparade ändringar")


def _check_head(worktree: Path, expected_commit: str) -> StepResult:
    proc = _run(["git", "rev-parse", "HEAD"], cwd=worktree)
    if proc.returncode != 0:
        return StepResult("HEAD", False, _tail(proc.stderr))
    actual = proc.stdout.strip()
    if actual != expected_commit:
        return StepResult("HEAD", False,
                          f"förväntade {expected_commit[:10]}, fick {actual[:10]}")
    return StepResult("HEAD", True, actual[:10])


def _merge(branch: str, message: str) -> StepResult:
    proc = _run(["git", "merge", "--no-ff", branch, "-m", message], cwd=APP_ROOT)
    if proc.returncode != 0:
        return StepResult("merge", False, _tail(proc.stdout + proc.stderr))
    return StepResult("merge", True, f"mergade {branch}")


def _check_after_merge() -> StepResult:
    proc = _run([sys.executable, "-B", "-m", "scripts.check"], cwd=APP_ROOT)
    if proc.returncode != 0:
        return StepResult("scripts.check (efter merge)", False,
                          _tail(proc.stdout + proc.stderr))
    return StepResult("scripts.check (efter merge)", True, "godkänd")


def _cleanup(worktree: Path, branch: str) -> StepResult:
    proc = _run(["git", "worktree", "remove", str(worktree)], cwd=APP_ROOT)
    if proc.returncode != 0:
        return StepResult("städning", False, _tail(proc.stderr))
    proc = _run(["git", "branch", "-D", branch], cwd=APP_ROOT)
    if proc.returncode != 0:
        return StepResult("städning", False, _tail(proc.stderr))
    return StepResult("städning", True, f"tog bort {worktree} och {branch}")


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
    lines.append(f"- Resultat: {'OK' if overall_ok else 'MISSLYCKADES'}")
    lines.append(f"- Verifierad: {dt.datetime.now().astimezone().isoformat(timespec='seconds')}")
    for s in steps:
        marker = "OK" if s.ok else "FEL"
        first = s.detail.splitlines()[0] if s.detail else ""
        lines.append(f"- [{marker}] {s.name}: {first}")
    report.write_text(text + "\n".join(lines) + "\n")


def _print_step(step: StepResult) -> None:
    marker = "OK" if step.ok else "FEL"
    first = step.detail.splitlines()[0] if step.detail else ""
    print(f"[{marker}] {step.name}: {first}")
    if not step.ok and step.detail:
        for line in step.detail.splitlines()[1:]:
            print(f"       {line}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Verifiera och merga en run")
    parser.add_argument("run", help="t.ex. 3 eller 2026-10-20_3")
    parser.add_argument("--dry-run", action="store_true",
                        help="Verifiera men merga/städa inte")
    parser.add_argument("--no-cleanup", action="store_true",
                        help="Behåll worktreen efter merge")
    parser.add_argument("--fast", action="store_true",
                        help="Använd bara deepseek-tester, inte hela scripts.check")
    args = parser.parse_args(argv)

    history = _load_history()
    entry = _resolve_run(history, args.run)
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

    if not record(_run_deepseek_tests(worktree)):
        _append_report(entry, steps, overall_ok)
        print(f"\nWorktree behålls för inspektion: {worktree}")
        return 1

    if not record(_run_full_check(worktree, fast=args.fast)):
        _append_report(entry, steps, overall_ok)
        print(f"\nWorktree behålls för inspektion: {worktree}")
        return 1

    if not record(_check_clean(worktree)):
        _append_report(entry, steps, overall_ok)
        print(f"\nWorktree behålls för inspektion: {worktree}")
        return 1

    if not record(_check_head(worktree, entry["commit"])):
        _append_report(entry, steps, overall_ok)
        print(f"\nWorktree behålls för inspektion: {worktree}")
        return 1

    if args.dry_run:
        print("\n--dry-run: hoppar över merge och städning.")
        _append_report(entry, steps, overall_ok)
        return 0

    merge_msg = (f"Merge autonomous run {entry['date']}_{entry['run']}: "
                 f"{entry.get('task_preview', '')[:60]}")
    if not record(_merge(entry["branch"], merge_msg)):
        _append_report(entry, steps, overall_ok)
        print("\nMerge misslyckades. Worktree behålls.")
        return 1

    if not record(_check_after_merge()):
        _append_report(entry, steps, overall_ok)
        print("\nOBS: merge är redan gjord. Backa med 'git reset --hard ORIG_HEAD'.")
        return 1

    if not args.no_cleanup:
        record(_cleanup(worktree, entry["branch"]))

    _append_report(entry, steps, overall_ok)
    print(f"\nSammanfattning: {'OK' if overall_ok else 'MISSLYCKADES'}")
    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())
