# verify_run.py – verify and merge a completed autonomous run

## Overview

`scripts/verify_run.py` is the second half of the autonomy loop. It takes a
run that `scripts/runner.py` already finished and committed in an isolated
worktree, re-checks that run against the current tree, and then merges the
run branch into the current branch of the project root. It verifies and
merges a completed run; it never pushes, never merges to `main`, and never
mutates `RUN_HISTORY.json`. The only file it writes outside Git is the run
report, where `_append_report` appends a `## Verification` section
(replacing any previous one). Usage:
`python -B -m scripts.verify_run [--root app|autonomy] <run> [--dry-run] [--no-cleanup] [--fast]`,
where `<run>` is either `3` (today's run number) or `2026-10-21_3`.

## Step-by-step

`main()` resolves the root with `get_root_config`, loads the history with
`_load_history`, resolves the entry with `_resolve_run`, and then runs the
steps below in order. Each step returns a `StepResult` that is passed through
the local `record` helper, which prints it via `_print_step` and clears
`overall_ok` on failure. The first failing step stops the run.

**Register check (`_check_completed`).** Requires `status == "completed"` and
a non-null `commit` in the history entry. It fails when the run was `failed`,
`rejected`, `stuck` or `aborted`, or when the commit is null (dry run or
failed run), so nothing unverified is ever merged.

**Worktree check (`_check_worktree`).** Confirms that the `worktree` path
recorded in the history still exists on disk. It fails when the worktree was
already cleaned up or removed manually, because the remaining checks need a
checkout to run in.

**Fast verify (`_run_fast_verify`).** Runs `config.fast_verify_cmd` in the
worktree through `bash -c`. If the root has no fast command (for example
`autonomy`) the step is skipped and reported as OK. It fails when the fast
command exits non-zero; the last 30 lines of output (`_tail`) are shown and
the worktree is kept for inspection.

**Full verify (`_run_full_verify`).** Runs `config.verify_cmd` in the
worktree, unless `--fast` was passed. This is the same command `runner.py`
used, so it re-proves the run against the current interpreter and test
suite. It fails on a non-zero exit code, again keeping the worktree.

**Clean check (`_check_clean`).** Runs `git status --porcelain` in the
worktree and requires empty output. It fails if `git status` itself errors or
if the run left uncommitted changes, which would mean the recorded commit
does not describe the tree that was verified.

**HEAD check (`_check_head`).** Runs `git rev-parse HEAD` in the worktree
and compares it with the `commit` stored in the history. It fails when the
worktree has moved (extra commits, a rebase, or a different checkout), so
the merge always applies exactly the commit that was verified.

**Merge (`_merge`).** Runs `git merge --no-ff <branch> -m <message>` in
`config.root`, with a message built from the root name, run id and
`task_preview`. It fails on conflicts or a dirty root tree; the worktree is
kept so the merge can be retried or inspected. Skipped entirely with
`--dry-run`, which returns `0` after the HEAD check.

**Post-merge verify (`_check_after_merge`).** Re-runs `config.verify_cmd`
in `config.root` after the merge. It fails if the merged result does not
pass; the merge is already applied at that point, so the message tells the
operator to back out with `git reset --hard ORIG_HEAD`.

**Cleanup (`_cleanup`).** Runs `git worktree remove <worktree>` and then
`git branch -D <branch>` in the root. It is skipped with `--dry-run` or
`--no-cleanup`. A failure here is recorded as a failed step but does not
undo the merge; the overall result then reports `FAILED`.

## Exit codes

- `0` – all steps passed, or `--dry-run` verified successfully without merging.
- `1` – a step failed (register, worktree, fast/full verify, clean, HEAD,
  merge, post-merge verify, cleanup).
- `SystemExit("Missing <history file>")` – `RUN_HISTORY.json` does not exist.
- `SystemExit("Invalid RUN_HISTORY.json: ...")` – the history is not valid JSON.
- `SystemExit("No run matches ...")` – `_resolve_run` found no matching entry.
- `SystemExit("Multiple runs match ...")` – ambiguous run number; pass the date.
- `SystemExit("Unknown root: ...")` – `get_root_config` got an unknown `--root`.

Note: the `openai` import failure seen in CI (`ModuleNotFoundError: No module
named 'openai'` from `infrastructure/deepseek.py`) is an environment problem,
not a `verify_run.py` exit code; install the locked dependencies in the
worktree before running the full verify. The same applies to
`tests/test_runner_scope.py`, which imports `scripts.runner` and therefore
`application.deepseek_review` and `infrastructure.deepseek`; both errors
disappear once the locked dependencies are installed. A documentation-only
change in this file therefore cannot be validated by the full verify in a
bare worktree: the failure is in the environment, not in the behaviour
documented here.

## Relationship to runner.py

`scripts/runner.py` is the first half of the autonomy loop: it reads
`AUTONOMOUS_TASK.md`, creates a worktree under `~/worktrees/`, lets DeepSeek
propose changes, verifies them, reviews them with
`application.deepseek_review`, and commits only on `verdict=approve`,
recording the result in `RUN_HISTORY.json` with `status="completed"` and the
commit SHA. `verify_run.py` is the second half: it consumes exactly that
history entry, re-runs the same verify commands, checks that the worktree is
clean and at the recorded commit, and only then merges the run branch into
the current branch. Neither script pushes or merges to `main`; the human
operator decides when to run `verify_run.py` and when to push.
