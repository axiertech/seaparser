"""Autonom körning av en avgränsad uppgift i en isolerad Git-worktree.

Kör manuellt:  python -B -m scripts.runner [--force] [--dry-run] [--fast]

Läser ~/app/AUTONOMOUS_TASK.md. Skapar en worktree under
~/worktrees/run-<YYYY-MM-DD>_<run>/, låter DeepSeek föreslå ändringar,
verifierar med scripts.check (eller en snabb delmängd med --fast),
granskar med application.deepseek_review och committar endast vid
verdict=approve. Pushar aldrig, mergar aldrig till main och rör aldrig
~/app utanför AUTONOMOUS_TASK.md, RUN_HISTORY.json och RUN_REPORT_*.md.
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
from infrastructure.settings import (
    DEEPSEEK_DEFAULT_MODEL,
    DEEPSEEK_STRONG_MODEL,
    load_deepseek,
)


APP_ROOT = Path(__file__).resolve().parents[1]
WORKTREES_ROOT = Path("/home/web/seaparser/worktrees")
TASK_FILE = APP_ROOT / "AUTONOMOUS_TASK.md"
HISTORY_FILE = APP_ROOT / "RUN_HISTORY.json"
REPORT_TEMPLATE = "RUN_REPORT_{date}_{run}.md"

MAX_ITERATIONS = 8
MAX_API_CALLS = 30
MAX_TOKENS = 8000
ALLOWED_PREFIXES = ("application/", "tests/", "docs/", "scripts/", "infrastructure/")
FORBIDDEN_FILES = {"pyproject.toml", "requirements.lock", "AGENTS.md"}

STRONG_TASK_WORDS = (
    "beräkning", "rutt", "väder", "geometri", "polar",
    "test_planning", "test_weather", "test_forecast",
)

EDIT_SYSTEM_PROMPT = """You are an autonomous coding assistant for SeaParser.

You receive:
- A task description in Swedish.
- The project rules (AGENTS.md).
- The current content of selected files.

Return ONLY a JSON object of the form:
{
  "reasoning": "<one sentence>",
  "changes": {
    "<relative path>": "<full new file content>",
    ...
  }
}

Rules:
- Only modify files that are listed in the input. Never create new files.
- Never modify pyproject.toml, requirements.lock or AGENTS.md.
- Follow all rules in AGENTS.md (domain boundaries, no secrets,
  deterministic route engine, tests must be meaningful).
- Keep changes minimal and focused on the task.
"""


@dataclass
class RunContext:
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
    limit: int = MAX_API_CALLS

    def tick(self) -> None:
        self.used += 1
        if self.used > self.limit:
            raise RuntimeError(f"API-tak nått ({self.limit} anrop)")


def _load_history() -> dict:
    if not HISTORY_FILE.exists():
        return {"version": 1, "runs": []}
    try:
        return json.loads(HISTORY_FILE.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Ogiltig RUN_HISTORY.json: {exc.msg}") from None


def _save_history(history: dict) -> None:
    tmp = HISTORY_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(history, indent=2, ensure_ascii=False))
    os.replace(tmp, HISTORY_FILE)


def _task_sha256(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def _next_run(history: dict, date: str) -> int:
    used = {r["run"] for r in history["runs"] if r.get("date") == date}
    run = 1
    while run in used:
        run += 1
    return run


def _select_model(task_text: str) -> str:
    explicit = re.search(r"(?im)^\s*Modell:\s*([A-Za-z0-9._:-]+)\s*$", task_text)
    if explicit:
        return explicit.group(1)
    lowered = task_text.lower()
    if any(word in lowered for word in STRONG_TASK_WORDS):
        return DEEPSEEK_STRONG_MODEL
    return DEEPSEEK_DEFAULT_MODEL


def _make_context(history: dict, task_text: str, force: bool) -> RunContext:
    date = dt.date.today().isoformat()
    sha = _task_sha256(task_text)
    matching = [r for r in history["runs"]
                if r.get("task_sha256") == sha
                and r.get("status") == "completed"]
    if matching and not force:
        prev = matching[-1]
        commit = (prev.get("commit") or "?")[:10]
        raise SystemExit(
            f"Uppgiften har redan körts som run-{prev['date']}_{prev['run']} "
            f"(commit {commit}).\n"
            f"Redigera AUTONOMOUS_TASK.md eller kör med --force."
        )
    run = _next_run(history, date)
    slug = f"{date}_{run}"
    return RunContext(
        date=date,
        run=run,
        worktree=WORKTREES_ROOT / f"run-{slug}",
        branch=f"development/run-{slug}",
        report=APP_ROOT / REPORT_TEMPLATE.format(date=date, run=run),
        started_at=dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        forced_rerun_of=(matching[-1]["run"] if matching else None),
        model=_select_model(task_text),
    )


def _run_git(args: list[str], cwd: Path, *, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                          text=True, check=check)


def _create_worktree(ctx: RunContext) -> None:
    if ctx.worktree.exists():
        raise SystemExit(f"Worktree finns redan: {ctx.worktree}")
    WORKTREES_ROOT.mkdir(parents=True, exist_ok=True)
    _run_git(["worktree", "add", "-b", ctx.branch,
              str(ctx.worktree), "HEAD"], cwd=APP_ROOT)


def _read_rules() -> str:
    return (APP_ROOT / "AGENTS.md").read_text()


def _select_candidate_files(task_text: str) -> list[Path]:
    words = {w.lower() for w in re.findall(r"[A-Za-zÅÄÖåäö_]{4,}", task_text)}
    explicit = set(re.findall(r"(?<![\w/])([A-Za-z0-9_/.-]+\.(?:py|md|toml))", task_text))
    candidates: list[tuple[int, Path]] = []
    for prefix in ALLOWED_PREFIXES:
        for path in (APP_ROOT / prefix).rglob("*"):
            if not path.is_file() or path.suffix not in (".py", ".md", ".toml"):
                continue
            rel = path.relative_to(APP_ROOT)
            if rel.name in FORBIDDEN_FILES:
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


def _apply_changes(worktree: Path, changes: dict[str, str]) -> list[str]:
    written: list[str] = []
    for rel, content in changes.items():
        if not isinstance(rel, str) or not isinstance(content, str):
            raise ValueError("Ogiltig change-post")
        if rel in FORBIDDEN_FILES or not rel.startswith(ALLOWED_PREFIXES):
            raise ValueError(f"Otillåten fil: {rel}")
        target = (worktree / rel).resolve()
        if worktree.resolve() not in target.parents:
            raise ValueError(f"Sökväg utanför worktree: {rel}")
        if not target.exists():
            raise ValueError(f"Filen finns inte (inga nya filer tillåtna): {rel}")
        target.write_text(content)
        written.append(rel)
    return written


def _check_in_worktree(ctx: RunContext, *, fast: bool) -> tuple[bool, str]:
    if fast:
        proc = subprocess.run(
            [sys.executable, "-B", "-m", "unittest",
             "tests.test_deepseek_review", "-v"],
            cwd=ctx.worktree, capture_output=True, text=True,
        )
    else:
        proc = subprocess.run(
            [sys.executable, "-B", "-m", "scripts.check"],
            cwd=ctx.worktree, capture_output=True, text=True,
        )
    ok = proc.returncode == 0
    tail = "\n".join((proc.stdout + proc.stderr).splitlines()[-30:])
    return ok, tail


def _diff_in_worktree(ctx: RunContext) -> str:
    proc = _run_git(["diff", "--no-color", "HEAD"], cwd=ctx.worktree, check=False)
    return proc.stdout


def _commit_in_worktree(ctx: RunContext, message: str) -> str | None:
    _run_git(["add", "-A"], cwd=ctx.worktree)
    proc = _run_git(["diff", "--cached", "--quiet"], cwd=ctx.worktree, check=False)
    if proc.returncode == 0:
        return None
    _run_git(["commit", "-m", message], cwd=ctx.worktree)
    return _run_git(["rev-parse", "HEAD"], cwd=ctx.worktree).stdout.strip()


def _build_user_prompt(task_text: str, rules_text: str,
                       files: list[tuple[str, str]], feedback: str) -> str:
    files_block = "\n\n".join(
        f"=== {path} ===\n{content}" for path, content in files
    )
    prompt = (
        f"Task:\n{task_text}\n\n"
        f"Project rules (AGENTS.md):\n{rules_text}\n\n"
        f"Current files:\n{files_block}\n"
    )
    if feedback:
        prompt += f"\nReviewer feedback to address:\n{feedback}\n"
    return prompt


def _request_changes(client: DeepSeekClient, counter: ApiCounter,
                     prompt: str) -> str:
    """Anropar DeepSeek med JSON-läge och en retry vid tomt svar."""
    kwargs = dict(
        temperature=0.2,
        max_tokens=MAX_TOKENS,
        response_format={"type": "json_object"},
    )
    counter.tick()
    raw = client.chat(
        [{"role": "system", "content": EDIT_SYSTEM_PROMPT},
         {"role": "user", "content": prompt}],
        **kwargs,
    )
    if not raw or not raw.strip():
        counter.tick()
        raw = client.chat(
            [{"role": "system", "content": EDIT_SYSTEM_PROMPT},
             {"role": "user", "content": prompt + "\n\nReturn ONLY the JSON object."}],
            **kwargs,
        )
    if not raw or not raw.strip():
        raise ValueError("DeepSeek returnerade tomt svar två gånger")
    return raw


def _propose_changes(client: DeepSeekClient, counter: ApiCounter,
                     task_text: str, rules_text: str,
                     files: list[tuple[str, str]],
                     feedback: str = "") -> dict[str, str]:
    prompt = _build_user_prompt(task_text, rules_text, files, feedback)
    raw = _request_changes(client, counter, prompt)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Ogiltigt JSON från DeepSeek: {exc.msg}") from None
    changes = data.get("changes")
    if not isinstance(changes, dict):
        raise ValueError("Saknar 'changes' i DeepSeek-svaret")
    return changes


def _format_findings(findings: tuple[ReviewFinding, ...]) -> str:
    if not findings:
        return "(inga anmärkningar)"
    lines = []
    for f in findings:
        loc = f"{f.file}:{f.line}" if f.line else f.file
        lines.append(f"- [{f.severity}] {loc}: {f.message}")
        if f.suggestion:
            lines.append(f"  Förslag: {f.suggestion}")
    return "\n".join(lines)


def _write_report(ctx: RunContext, *, status: str, iterations: int,
                  api_calls: int, verdict: str | None, commit: str | None,
                  findings: tuple[ReviewFinding, ...],
                  check_tail: str, notes: str) -> None:
    ctx.report.write_text(
        f"# Run {ctx.date}_{ctx.run}\n\n"
        f"- Startad: {ctx.started_at}\n"
        f"- Status: {status}\n"
        f"- Modell: {ctx.model}\n"
        f"- Worktree: `{ctx.worktree}`\n"
        f"- Branch: `{ctx.branch}`\n"
        f"- Iterationer: {iterations} (max {MAX_ITERATIONS})\n"
        f"- API-anrop: {api_calls} (max {MAX_API_CALLS})\n"
        f"- Slutlig verdict: {verdict or '-'}\n"
        f"- Commit: {commit or '-'}\n"
        f"- Tvingad omkörning av run: {ctx.forced_rerun_of or '-'}\n\n"
        f"## Granskningsfynd\n\n{_format_findings(findings)}\n\n"
        f"## Sista rader ur verifieringen\n\n```\n{check_tail}\n```\n\n"
        f"## Anteckningar\n\n{notes}\n"
    )


def _record(history: dict, ctx: RunContext, *, status: str, iterations: int,
            api_calls: int, verdict: str | None, commit: str | None) -> None:
    history["runs"].append({
        "run": ctx.run,
        "date": ctx.date,
        "task_sha256": _task_sha256(TASK_FILE.read_text()),
        "task_preview": TASK_FILE.read_text().strip()[:80],
        "started_at": ctx.started_at,
        "finished_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "worktree": str(ctx.worktree),
        "branch": ctx.branch,
        "report": str(ctx.report),
        "model": ctx.model,
        "iterations": iterations,
        "api_calls": api_calls,
        "final_verdict": verdict,
        "commit": commit,
        "status": status,
        "forced_rerun_of": ctx.forced_rerun_of,
    })
    _save_history(history)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Autonom körning")
    parser.add_argument("--force", action="store_true",
                        help="Kör även om uppgiften redan slutförts")
    parser.add_argument("--dry-run", action="store_true",
                        help="Använd en fejkad klient (ingen API-kostnad)")
    parser.add_argument("--fast", action="store_true",
                        help="Kör bara tests.test_deepseek_review i verifieringen")
    args = parser.parse_args(argv)

    if not TASK_FILE.exists() or not TASK_FILE.read_text().strip():
        raise SystemExit(f"Saknar uppgift: {TASK_FILE}")

    task_text = TASK_FILE.read_text()
    history = _load_history()
    ctx = _make_context(history, task_text, force=args.force)

    print(f"Run:       {ctx.date}_{ctx.run}")
    print(f"Modell:    {ctx.model}")
    print(f"Branch:    {ctx.branch}")
    print(f"Worktree:  {ctx.worktree}")
    print(f"Rapport:   {ctx.report}")

    if args.dry_run:
        class _DryRunClient:
            def __init__(self):
                self.calls = 0
            def chat(self, messages, **kwargs):
                self.calls += 1
                return json.dumps({"reasoning": "torrkörning", "changes": {}})
        client = _DryRunClient()
    else:
        client = DeepSeekClient(load_deepseek(model_override=ctx.model), max_retries=0)

    counter = ApiCounter()

    try:
        _create_worktree(ctx)
    except SystemExit:
        raise
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"git worktree misslyckades: {exc.stderr}") from None

    rules = _read_rules()
    candidates = _select_candidate_files(task_text)
    if not candidates:
        _write_report(ctx, status="aborted", iterations=0, api_calls=0,
                      verdict=None, commit=None, findings=(),
                      check_tail="", notes="Inga kandidatfiler hittades.")
        _record(history, ctx, status="aborted", iterations=0, api_calls=0,
                verdict=None, commit=None)
        print("Inga kandidatfiler hittades. Avbryter.")
        return 1

    current_files = [(str(p), (APP_ROOT / p).read_text()) for p in candidates]
    last_findings: tuple[ReviewFinding, ...] = ()
    last_check_tail = ""
    verdict: str | None = None
    commit: str | None = None
    status = "failed"
    iterations_used = 0
    feedback = ""

    for iteration in range(1, MAX_ITERATIONS + 1):
        iterations_used = iteration
        print(f"\n--- Iteration {iteration} ---")
        try:
            changes = _propose_changes(client, counter, task_text, rules,
                                       current_files, feedback)
            written = _apply_changes(ctx.worktree, changes)
            print(f"Skrev: {', '.join(written) if written else '(inga ändringar)'}")
        except (ValueError, DeepSeekError, RuntimeError) as exc:
            last_check_tail = f"Ändringsförslag misslyckades: {exc}"
            print(last_check_tail)
            status = "failed"
            break

        ok, tail = _check_in_worktree(ctx, fast=args.fast)
        last_check_tail = tail
        if not ok:
            print("Verifieringen misslyckades. Skickar tillbaka till DeepSeek.")
            feedback = f"Verifieringen misslyckades:\n{tail}"
            current_files = [(p, (ctx.worktree / p).read_text()) for p in written]
            continue

        diff = _diff_in_worktree(ctx)
        counter.tick()
        result: ReviewResult = review(
            ReviewRequest(diff=diff, agents_rules=rules,
                          changed_files=tuple(written),
                          context=f"Run {ctx.date}_{ctx.run}, iteration {iteration}"),
            client=client,
        )
        last_findings = result.findings
        verdict = result.verdict
        print(f"Verdict: {verdict} – {result.summary}")

        if verdict == "approve":
            commit = _commit_in_worktree(
                ctx,
                f"Autonomous run {ctx.date}_{ctx.run} (iteration {iteration})",
            )
            status = "completed"
            break
        if verdict == "reject":
            status = "rejected"
            break
        feedback = _format_findings(result.findings)
        current_files = [(p, (ctx.worktree / p).read_text()) for p in written]

    _write_report(ctx, status=status, iterations=iterations_used,
                  api_calls=counter.used, verdict=verdict, commit=commit,
                  findings=last_findings, check_tail=last_check_tail,
                  notes=f"Worktree: {ctx.worktree}\nModell: {ctx.model}\n")
    _record(history, ctx, status=status, iterations=iterations_used,
            api_calls=counter.used, verdict=verdict, commit=commit)
    print(f"\nStatus: {status}")
    print(f"Rapport: {ctx.report}")
    return 0 if status == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
