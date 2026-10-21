"""Autonomous run of one bounded task in an isolated Git worktree.

Usage:  python -B -m scripts.runner [--root app|autonomy] [--force] [--dry-run] [--fast]

Reads <root>/AUTONOMOUS_TASK.md. Creates a worktree under
~/worktrees/<prefix>-<YYYY-MM-DD>_<run>/, lets DeepSeek propose changes via
Tool Calls, verifies with the per-root verify command, reviews with
application.deepseek_review, and commits only on verdict=approve. Never
pushes, never merges to main, never modifies <root> outside
AUTONOMOUS_TASK.md, RUN_HISTORY.json and RUN_REPORT_*.md.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from application.deepseek_review import (
    ReviewFinding,
    ReviewRequest,
    ReviewResult,
    review,
)
from infrastructure.deepseek import DeepSeekClient, DeepSeekError
from infrastructure.deepseek_tools import TOOLS, execute_tool
from infrastructure.roots import RootConfig, get_root_config
from infrastructure.settings import (
    DEEPSEEK_DEFAULT_MODEL,
    DEEPSEEK_STRONG_MODEL,
    load_deepseek,
)


STRONG_TASK_WORDS = (
    "beräkning", "rutt", "väder", "geometri", "polar",
    "test_planning", "test_weather", "test_forecast",
    "git", "plan", "arkitektur", "refaktorera", "kodbas", "långsiktig",
    "architecture", "refactor", "codebase", "long-term",
)

EDIT_SYSTEM_PROMPT = """You are an autonomous coding assistant.

You have access to tools:
- read_file(path)
- write_file(path, content)
- run_command(command)

Use them to complete the task. Follow the project rules provided in the
user message. Never modify forbidden files listed there. Keep changes
minimal and focused.

IMPORTANT - work efficiently:
- Read at most 3 files before deciding what to change. Do not re-read
  files you have already seen.
- Write files as soon as you understand the change. Do not spend more
  than 3 tool rounds exploring before the first write_file.
- If the task spans multiple files, write them one by one. Do not
  batch-explore all of them first.
- If you cannot complete the full task in the remaining rounds, write
  the files you have figured out and stop cleanly. A partial change
  that compiles is better than no change at all.

IMPORTANT - work efficiently:
- Read at most 3 files before deciding what to change. Do not re-read
  files you have already seen.
- Write files as soon as you understand the change. Do not spend more
  than 3 tool rounds exploring before the first write_file.
- If the task spans multiple files, write them one by one. Do not
  batch-explore all of them first.
- If you cannot complete the full task in the remaining rounds, write
  the files you have figured out and stop cleanly. A partial change
  that compiles is better than no change at all.

Code style rules (from AGENTS.md):
- Prefer module-level functions over nested functions or closures. Only
  use a nested function for decorators, single-call-site helpers, or
  closures that genuinely capture loop variables. If a helper is used
  more than once, or is longer than ~10 lines, move it to module level.
- Every function and method you write must have a docstring. One line
  for simple functions, Args/Returns/Raises for non-obvious ones.
  Classes and modules get docstrings too.

When done, reply with a short summary and no more tool calls.
"""


@dataclass
class RunContext:
    config: RootConfig
    date: str
    run: int
    worktree: Path
    branch: str
    report: Path
    started_at: str
    forced_rerun_of: int | None
    model: str


@dataclass
class ApiCounter:
    used: int = 0
    limit: int = 30

    def tick(self) -> None:
        self.used += 1
        if self.used > self.limit:
            raise RuntimeError(f"API limit reached ({self.limit} calls)")


def _load_history(config: RootConfig) -> dict:
    if not config.history_file.exists():
        return {"version": 1, "runs": []}
    try:
        return json.loads(config.history_file.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid {config.history_file.name}: {exc.msg}") from None


def _save_history(config: RootConfig, history: dict) -> None:
    tmp = config.history_file.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(history, indent=2, ensure_ascii=False))
    os.replace(tmp, config.history_file)


def _task_sha256(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def _next_run(history: dict, date: str) -> int:
    used = {r["run"] for r in history["runs"] if r.get("date") == date}
    run = 1
    while run in used:
        run += 1
    return run


def _select_model(task_text: str) -> str:
    explicit = re.search(r"(?im)^\s*(?:Modell|Model):\s*([A-Za-z0-9._:-]+)\s*$", task_text)
    if explicit:
        return explicit.group(1)
    lowered = task_text.lower()
    if any(word in lowered for word in STRONG_TASK_WORDS):
        return DEEPSEEK_STRONG_MODEL
    return DEEPSEEK_DEFAULT_MODEL


def _max_tool_rounds_for_task(config: RootConfig, task_text: str) -> int:
    """Allow per-task override of max_tool_rounds via 'Max tool rounds: N'."""
    match = re.search(r"(?im)^\s*(?:Max tool rounds|Max tool calls):\s*(\d+)\s*$",
                      task_text)
    if match:
        return min(int(match.group(1)), 40)
    return config.max_tool_rounds


def _timeout_for_model(model: str) -> float:
    if model == DEEPSEEK_STRONG_MODEL:
        return 300.0
    return 90.0


def _max_tokens_for_model(config: RootConfig, model: str) -> int:
    if model == DEEPSEEK_STRONG_MODEL:
        return config.max_tokens_pro
    return config.max_tokens_flash


def _make_context(config: RootConfig, history: dict, task_text: str,
                  force: bool) -> RunContext:
    date = dt.date.today().isoformat()
    sha = _task_sha256(task_text)
    matching = [r for r in history["runs"]
                if r.get("task_sha256") == sha
                and r.get("status") == "completed"]
    if matching and not force:
        prev = matching[-1]
        commit = (prev.get("commit") or "?")[:10]
        raise SystemExit(
            f"Task already ran as {prev['date']}_{prev['run']} (commit {commit}).\n"
            f"Edit {config.task_file.name} or pass --force."
        )
    run = _next_run(history, date)
    return RunContext(
        config=config,
        date=date,
        run=run,
        worktree=config.worktree_path(date, run),
        branch=config.branch_name(date, run),
        report=config.report_path(date, run),
        started_at=dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        forced_rerun_of=(matching[-1]["run"] if matching else None),
        model=_select_model(task_text),
    )


def _run_git(args: list[str], cwd: Path, *, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                          text=True, check=check)


def _branch_exists(config: RootConfig, branch: str) -> bool:
    """Return True if the local branch exists."""
    proc = _run_git(["rev-parse", "--verify", branch],
                    cwd=config.root, check=False)
    return proc.returncode == 0


def _cleanup_stale_worktree(config: RootConfig, date: str, run: int,
                            force: bool) -> None:
    """Remove a stale worktree and branch for the given run.

    A worktree is stale if it exists but has no completed entry in
    RUN_HISTORY.json - that means a previous attempt was aborted before
    completion and left nothing of value. With force=True, remove
    regardless of history.
    """
    worktree = config.worktree_path(date, run)
    branch = config.branch_name(date, run)
    history = _load_history(config)
    has_completed = any(
        r.get("date") == date and r.get("run") == run
        and r.get("status") == "completed"
        for r in history["runs"]
    )
    has_worktree = worktree.exists()
    has_branch = _branch_exists(config, branch)

    if not has_worktree and not has_branch:
        return

    if has_completed and not force:
        raise SystemExit(
            f"Run {date}_{run} is completed and its worktree still exists. "
            f"Verify it with verify_run first, or pass --clean to overwrite."
        )

    if has_worktree:
        print(f"Removing stale worktree {worktree}")
        _run_git(["worktree", "remove", str(worktree), "--force"],
                 cwd=config.root, check=False)
    _run_git(["worktree", "prune"], cwd=config.root, check=False)

    if has_branch:
        print(f"Removing stale branch {branch}")
        _run_git(["branch", "-D", branch], cwd=config.root, check=False)


def _create_worktree(ctx: RunContext) -> None:
    """Create a new worktree for this run. Caller must have cleaned any stale one."""
    if ctx.worktree.exists():
        raise SystemExit(f"Worktree still exists after cleanup: {ctx.worktree}")
    ctx.config.worktrees_root.mkdir(parents=True, exist_ok=True)
    _run_git(["worktree", "add", "-b", ctx.branch,
              str(ctx.worktree), "HEAD"], cwd=ctx.config.root)


def _read_rules(config: RootConfig) -> str:
    return config.rules_file.read_text()


def _select_candidate_files(config: RootConfig, task_text: str) -> list[Path]:
    words = {w.lower() for w in re.findall(r"[A-Za-zÅÄÖåäö_]{4,}", task_text)}
    explicit = set(re.findall(r"(?<![\w/])([A-Za-z0-9_/.-]+\.(?:py|md|toml|sh))", task_text))
    candidates: list[tuple[int, Path]] = []
    for prefix in config.allowed_prefixes:
        base = config.root / prefix if prefix else config.root
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix not in (".py", ".md", ".toml", ".sh"):
                continue
            rel = path.relative_to(config.root)
            if rel.name in config.forbidden_files:
                continue
            if "logs/" in str(rel) or "cache/" in str(rel) or "archive/" in str(rel):
                continue
            try:
                text = path.read_text()
            except UnicodeDecodeError:
                continue
            score = sum(1 for w in words if w in text.lower())
            if str(rel) in explicit or rel.name in explicit:
                score += 100
            if score:
                candidates.append((score, rel))
    candidates.sort(key=lambda x: (-x[0], str(x[1])))
    return [p for _, p in candidates[:5]]


def _check_in_worktree(ctx: RunContext, *, fast: bool) -> tuple[bool, str]:
    cmd = ctx.config.fast_verify_cmd if fast and ctx.config.fast_verify_cmd else ctx.config.verify_cmd
    proc = subprocess.run(["bash", "-c", cmd], cwd=ctx.worktree,
                          capture_output=True, text=True)
    ok = proc.returncode == 0
    tail = "\n".join((proc.stdout + proc.stderr).splitlines()[-30:])
    return ok, tail


def _diff_in_worktree(ctx: RunContext) -> str:
    _run_git(["add", "-A"], cwd=ctx.worktree)
    proc = _run_git(["diff", "--cached", "--no-color"], cwd=ctx.worktree, check=False)
    return proc.stdout


def _commit_in_worktree(ctx: RunContext, message: str) -> str | None:
    """Stage all changes and commit. Return the new SHA, or None if nothing to commit."""
    _run_git(["add", "-A"], cwd=ctx.worktree)
    proc = _run_git(["diff", "--cached", "--quiet"], cwd=ctx.worktree, check=False)
    if proc.returncode == 0:
        return None
    commit_proc = _run_git(["commit", "-m", message], cwd=ctx.worktree, check=False)
    if commit_proc.returncode != 0:
        raise RuntimeError(
            f"git commit failed in {ctx.worktree}: "
            f"{(commit_proc.stderr or commit_proc.stdout).strip()[-300:]}"
        )
    return _run_git(["rev-parse", "HEAD"], cwd=ctx.worktree).stdout.strip()


def _build_user_prompt(ctx: RunContext, task_text: str, rules_text: str,
                       files: list[tuple[str, str]], feedback: str) -> str:
    files_block = "\n\n".join(f"=== {path} ===\n{content}" for path, content in files)
    forbidden = ", ".join(sorted(ctx.config.forbidden_files)) or "(none)"
    prompt = (
        f"Task:\n{task_text}\n\n"
        f"Project rules ({ctx.config.rules_file.name}):\n{rules_text}\n\n"
        f"Forbidden files (never write): {forbidden}\n\n"
        f"Current files:\n{files_block}\n"
    )
    if feedback:
        prompt += (
            "\n\nReviewer feedback (you MUST address this by calling write_file):\n"
            + feedback
            + "\n\nCall write_file to update the affected files, then call run_command "
              "to verify. Do not just describe what you would do."
        )
    return prompt


def _run_agent_loop(client: DeepSeekClient, ctx: RunContext, task_text: str,
                    rules_text: str, initial_files: list[tuple[str, str]],
                    counter: ApiCounter, feedback: str = "") -> tuple[list[str], str]:
    written: list[str] = []
    messages: list = [
        {"role": "system", "content": EDIT_SYSTEM_PROMPT},
        {"role": "user", "content": _build_user_prompt(ctx, task_text, rules_text,
                                                       initial_files, feedback)},
    ]
    last_text = ""
    max_tokens = _max_tokens_for_model(ctx.config, ctx.model)

    max_rounds = _max_tool_rounds_for_task(ctx.config, task_text)
    for round_num in range(max_rounds):
        print(f"  Tool round {round_num + 1}")
        counter.tick()
        message = client.chat_with_tools(messages, tools=TOOLS, max_tokens=max_tokens)
        messages.append(message)

        if not getattr(message, "tool_calls", None):
            last_text = getattr(message, "content", "") or ""
            print(f"  Done after {round_num + 1} rounds: {last_text[:120]}")
            return written, last_text

        for tool_call in message.tool_calls:
            name = tool_call.function.name
            args = tool_call.function.arguments
            print(f"    Tool: {name}")
            try:
                result = execute_tool(ctx.worktree, name, args,
                                      forbidden_files=ctx.config.forbidden_files)
                if name == "write_file":
                    try:
                        written.append(json.loads(args)["path"])
                    except Exception:
                        pass
            except Exception as exc:
                result = f"Error: {exc}"
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })

    print(f"  Reached max tool rounds ({max_rounds}).")
    return written, last_text


def _format_findings(findings: tuple[ReviewFinding, ...]) -> str:
    if not findings:
        return "(no findings)"
    lines = []
    for f in findings:
        loc = f"{f.file}:{f.line}" if f.line else f.file
        lines.append(f"- [{f.severity}] {loc}: {f.message}")
        if f.suggestion:
            lines.append(f"  Suggestion: {f.suggestion}")
    return "\n".join(lines)


def _write_report(ctx: RunContext, *, status: str, iterations: int,
                  api_calls: int, verdict: str | None, commit: str | None,
                  findings: tuple[ReviewFinding, ...],
                  check_tail: str, notes: str) -> None:
    ctx.report.write_text(
        f"# Run {ctx.date}_{ctx.run} ({ctx.config.name})\n\n"
        f"- Started: {ctx.started_at}\n"
        f"- Status: {status}\n"
        f"- Model: {ctx.model}\n"
        f"- Timeout: {_timeout_for_model(ctx.model)}s\n"
        f"- Max tokens: {_max_tokens_for_model(ctx.config, ctx.model)}\n"
        f"- Worktree: `{ctx.worktree}`\n"
        f"- Branch: `{ctx.branch}`\n"
        f"- Iterations: {iterations} (max {ctx.config.max_iterations})\n"
        f"- API calls: {api_calls} (max {ctx.config.max_api_calls})\n"
        f"- Final verdict: {verdict or '-'}\n"
        f"- Commit: {commit or '-'}\n"
        f"- Forced rerun of run: {ctx.forced_rerun_of or '-'}\n\n"
        f"## Reviewer findings\n\n{_format_findings(findings)}\n\n"
        f"## Last lines from verification\n\n```\n{check_tail}\n```\n\n"
        f"## Notes\n\n{notes}\n"
    )


def _record(ctx: RunContext, history: dict, *, status: str, iterations: int,
            api_calls: int, verdict: str | None, commit: str | None) -> None:
    history["runs"].append({
        "run": ctx.run,
        "date": ctx.date,
        "task_sha256": _task_sha256(ctx.config.task_file.read_text()),
        "task_preview": ctx.config.task_file.read_text().strip()[:80],
        "started_at": ctx.started_at,
        "finished_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "worktree": str(ctx.worktree),
        "branch": ctx.branch,
        "report": str(ctx.report),
        "model": ctx.model,
        "timeout_seconds": _timeout_for_model(ctx.model),
        "iterations": iterations,
        "api_calls": api_calls,
        "final_verdict": verdict,
        "commit": commit,
        "status": status,
        "forced_rerun_of": ctx.forced_rerun_of,
    })
    _save_history(ctx.config, history)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Autonomous run")
    parser.add_argument("--root", default="app", choices=["app", "autonomy"],
                        help="Which project root to run against")
    parser.add_argument("--force", action="store_true",
                        help="Run even if the task already completed")
    parser.add_argument("--dry-run", action="store_true",
                        help="Use a fake client (no API cost)")
    parser.add_argument("--fast", action="store_true",
                        help="Use the per-root fast verify command")
    parser.add_argument("--clean", action="store_true",
                        help="Remove stale worktree/branch for this run before starting")
    args = parser.parse_args(argv)

    config = get_root_config(args.root)

    if not config.task_file.exists() or not config.task_file.read_text().strip():
        raise SystemExit(f"Missing task: {config.task_file}")

    task_text = config.task_file.read_text()
    history = _load_history(config)
    ctx = _make_context(config, history, task_text, force=args.force)

    print(f"Root:      {ctx.config.name} ({ctx.config.root})")
    print(f"Run:       {ctx.date}_{ctx.run}")
    print(f"Model:     {ctx.model}")
    print(f"Timeout:   {_timeout_for_model(ctx.model)}s")
    print(f"Max tokens:{_max_tokens_for_model(ctx.config, ctx.model)}")
    print(f"Branch:    {ctx.branch}")
    print(f"Worktree:  {ctx.worktree}")
    print(f"Report:    {ctx.report}")

    if args.dry_run:
        class _DryRunClient:
            def __init__(self):
                self.calls = 0
            def chat_with_tools(self, messages, **kwargs):
                self.calls += 1
                return type("Msg", (), {
                    "content": "dry run",
                    "tool_calls": None,
                })()
        client = _DryRunClient()
    else:
        client = DeepSeekClient(
            load_deepseek(model_override=ctx.model),
            max_retries=1,
            timeout_seconds=_timeout_for_model(ctx.model),
        )

    counter = ApiCounter(limit=ctx.config.max_api_calls)

    try:
        _cleanup_stale_worktree(config, ctx.date, ctx.run, force=args.clean)
        _create_worktree(ctx)
    except SystemExit:
        raise
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"git worktree failed: {exc.stderr}") from None

    rules = _read_rules(config)
    candidates = _select_candidate_files(config, task_text)
    if not candidates:
        _write_report(ctx, status="aborted", iterations=0, api_calls=0,
                      verdict=None, commit=None, findings=(),
                      check_tail="", notes="No candidate files found.")
        _record(ctx, history, status="aborted", iterations=0, api_calls=0,
                verdict=None, commit=None)
        print("No candidate files found. Aborting.")
        return 1

    current_files = [(str(p), (config.root / p).read_text()) for p in candidates]
    last_findings: tuple[ReviewFinding, ...] = ()
    last_check_tail = ""
    verdict: str | None = None
    commit: str | None = None
    status = "failed"
    iterations_used = 0
    feedback = ""

    for iteration in range(1, config.max_iterations + 1):
        iterations_used = iteration
        print(f"\n--- Iteration {iteration} ---")
        try:
            written, last_text = _run_agent_loop(
                client, ctx, task_text, rules, current_files, counter,
                feedback=feedback,
            )
            if not written:
                print("No files written. Aborting.")
                last_check_tail = last_text
                status = "failed"
                break
            print(f"Wrote: {', '.join(written)}")
        except (DeepSeekError, RuntimeError) as exc:
            last_check_tail = f"Agent loop failed: {exc}"
            print(last_check_tail)
            status = "failed"
            break

        ok, tail = _check_in_worktree(ctx, fast=args.fast)
        last_check_tail = tail
        if not ok:
            print("Verification failed. Sending back to DeepSeek.")
            feedback = f"Verification failed:\n{tail}"
            current_files = [(p, (ctx.worktree / p).read_text())
                             for p in written if (ctx.worktree / p).exists()]
            continue

        diff = _diff_in_worktree(ctx)
        try:
            counter.tick()
            result: ReviewResult = review(
                ReviewRequest(diff=diff, agents_rules=rules,
                              changed_files=tuple(written),
                              context=f"Run {ctx.date}_{ctx.run} ({ctx.config.name}), iteration {iteration}"),
                client=client,
            )
        except (DeepSeekError, RuntimeError) as exc:
            last_check_tail = f"Reviewer failed: {exc}"
            print(last_check_tail)
            status = "failed"
            break
        last_findings = result.findings
        verdict = result.verdict
        print(f"Verdict: {verdict} - {result.summary}")

        if verdict == "approve":
            try:
                commit = _commit_in_worktree(
                    ctx,
                    f"Autonomous {ctx.config.name} run {ctx.date}_{ctx.run} (iteration {iteration})",
                )
            except RuntimeError as exc:
                last_check_tail = f"Commit failed: {exc}"
                print(last_check_tail)
                status = "failed"
                break
            status = "completed"
            break
        if verdict == "reject":
            status = "rejected"
            break
        feedback = _format_findings(result.findings)
        current_files = [(p, (ctx.worktree / p).read_text())
                         for p in written if (ctx.worktree / p).exists()]

    _write_report(ctx, status=status, iterations=iterations_used,
                  api_calls=counter.used, verdict=verdict, commit=commit,
                  findings=last_findings, check_tail=last_check_tail,
                  notes=f"Worktree: {ctx.worktree}\nModel: {ctx.model}\n")
    _record(ctx, history, status=status, iterations=iterations_used,
            api_calls=counter.used, verdict=verdict, commit=commit)
    print(f"\nStatus: {status}")
    print(f"Report: {ctx.report}")
    return 0 if status == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
