"""Kodgranskning via DeepSeek. Endast applikationslager.

Rör aldrig filer, kör aldrig kommandon och gör inga antaganden om
repo-state. Tar en fryst ReviewRequest och returnerar en strukturerad
ReviewResult. Ruttmotorn anropar aldrig denna modul.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Literal

from infrastructure.deepseek import DeepSeekClient, DeepSeekError
from infrastructure.settings import load_deepseek


# Begränsar hur stor diff som skickas till DeepSeek. Större diffar trunkeras
# och rapporteras som en warning-finding så att granskningen ses som ofullständig.
MAX_DIFF_CHARS = 20_000
MAX_RULES_CHARS = 20_000

_SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9]{10,}"),
    re.compile(r"(?i)password\s*=\s*\S+"),
    re.compile(r"BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY"),
)

_SYSTEM_PROMPT = """You are a strict code reviewer for the SeaParser project.

Rules you must enforce (from AGENTS.md):
- Domain layer (route engine) must not import HTTP clients, SQL, or UI code.
- No secrets, API keys, passwords, or private keys may appear in diffs,
  logs, docs, or test data.
- Dependencies must be exact-pinned and hash-locked where applicable.
- Unknown or stale forecasts must never be treated as safe.
- Land mask is not proof of navigability.
- Absolute limits cannot be outweighed by comfort scores or time savings.
- Estimated boat data must be clearly labelled.
- Tests must verify requirements and known results, not just mirror the
  implementation.
- New functionality must be discussed with the user before being merged
  to main.
- New or changed functions must be at module level, not nested closures
  (except decorators, single-call-site helpers, or genuine loop-variable
  capture). A nested function that could be moved to module level is a
  `nit` finding.
- New or changed functions and methods must have a docstring (one line
  for simple functions, Args/Returns/Raises for non-obvious ones).
  Missing docstring on a new or changed function is a `warning` finding.

Return ONLY a JSON object with this exact shape:
{
  "verdict": "approve" | "request_changes" | "reject",
  "summary": "<one or two sentences in Swedish>",
  "findings": [
    {
      "file": "<path>",
      "line": <int or null>,
      "severity": "blocker" | "warning" | "nit",
      "message": "<short Swedish description>",
      "suggestion": "<optional Swedish suggestion>"
    }
  ]
}

Rules for verdict:
- Any blocker finding MUST force verdict to "request_changes" or "reject".
- "approve" only if there are no blocker or warning findings.
- "reject" if the diff violates an absolute rule (secrets, domain
  boundary, hard weather limit bypass, test data as real data).
"""


@dataclass(frozen=True)
class ReviewRequest:
    diff: str
    agents_rules: str
    changed_files: tuple[str, ...]
    context: str = ""
    base_files: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReviewFinding:
    file: str
    line: int | None
    severity: Literal["blocker", "warning", "nit"]
    message: str
    suggestion: str = ""


@dataclass(frozen=True)
class ReviewResult:
    verdict: Literal["approve", "request_changes", "reject"]
    summary: str
    findings: tuple[ReviewFinding, ...] = field(default_factory=tuple)


class ReviewParseError(RuntimeError):
    """DeepSeek returnerade ett svar som inte matchar ReviewResult-schemat."""


def _find_secret_like(text: str) -> list[str]:
    hits = []
    for pattern in _SECRET_PATTERNS:
        for match in pattern.finditer(text):
            snippet = match.group(0)
            hits.append(snippet[:6] + "…")
    return hits


def _truncate(text: str, limit: int) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    return text[:limit] + "\n…[trunkerad]", True


def _parse_response(raw: str) -> ReviewResult:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ReviewParseError(f"Ogiltigt JSON från DeepSeek: {exc.msg}") from None
    if not isinstance(data, dict):
        raise ReviewParseError("DeepSeek-svaret är inte ett JSON-objekt")
    verdict = data.get("verdict")
    if verdict not in ("approve", "request_changes", "reject"):
        raise ReviewParseError(f"Ogiltig verdict: {verdict!r}")
    summary = data.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        raise ReviewParseError("Sammanfattning saknas")
    raw_findings = data.get("findings", [])
    if not isinstance(raw_findings, list):
        raise ReviewParseError("findings är inte en lista")
    findings: list[ReviewFinding] = []
    for item in raw_findings:
        if not isinstance(item, dict):
            raise ReviewParseError("finding är inte ett objekt")
        file = item.get("file")
        severity = item.get("severity")
        message = item.get("message")
        line = item.get("line")
        suggestion = item.get("suggestion", "")
        if not isinstance(file, str) or not file:
            raise ReviewParseError("finding saknar file")
        if severity not in ("blocker", "warning", "nit"):
            raise ReviewParseError(f"Ogiltig severity: {severity!r}")
        if not isinstance(message, str) or not message:
            raise ReviewParseError("finding saknar message")
        if line is not None and not isinstance(line, int):
            raise ReviewParseError("line måste vara int eller null")
        if not isinstance(suggestion, str):
            raise ReviewParseError("suggestion måste vara sträng")
        findings.append(ReviewFinding(
            file=file, line=line, severity=severity,
            message=message, suggestion=suggestion,
        ))
    if any(f.severity == "blocker" for f in findings) and verdict == "approve":
        raise ReviewParseError("blocker-finding kan inte ha verdict approve")
    return ReviewResult(verdict=verdict, summary=summary,
                        findings=tuple(findings))


def review(request: ReviewRequest, *,
           client: DeepSeekClient | None = None) -> ReviewResult:
    """Granskar en diff och returnerar ett strukturerat ReviewResult.

    Om ``request.diff`` är tom eller bara innehåller whitespace returneras
    ``ReviewResult(verdict="approve", summary="Inga ändringar att granska.")``
    direkt, utan att DeepSeek anropas. Detta besparar ett betalt API-anrop när
    det inte finns något att granska. I alla andra fall anropas ``client``
    (eller en klient som skapas från ``load_deepseek()``) och svaret tolkas av
    ``_parse_response``.
    """
    if not request.diff.strip():
        return ReviewResult(verdict="approve", summary="Inga ändringar att granska.")

    diff_text, diff_truncated = _truncate(request.diff, MAX_DIFF_CHARS)
    rules_text, rules_truncated = _truncate(request.agents_rules, MAX_RULES_CHARS)

    secret_hits = _find_secret_like(diff_text)
    injected_findings: list[ReviewFinding] = []
    if secret_hits:
        injected_findings.append(ReviewFinding(
            file="<diff>", line=None, severity="blocker",
            message=f"Möjliga hemligheter i diffen: {', '.join(secret_hits)}",
            suggestion="Ta bort hemligheten och rotera nyckeln om den läckt.",
        ))
    if diff_truncated:
        injected_findings.append(ReviewFinding(
            file="<diff>", line=None, severity="warning",
            message=f"Diffen trunkerades till {MAX_DIFF_CHARS} tecken; "
                    f"granskningen är ofullständig.",
        ))
    if rules_truncated:
        injected_findings.append(ReviewFinding(
            file="AGENTS.md", line=None, severity="warning",
            message=f"Reglerna trunkerades till {MAX_RULES_CHARS} tecken.",
        ))

    base_note = ""
    if request.base_files:
        base_note = (
            "\n\nFiles already present in the base commit (do NOT report "
            "them as missing - they exist in the tree):\n"
            + "\n".join(request.base_files)
        )
    user_prompt = (
        "Changed files:\n" + "\n".join(request.changed_files) +
        ("\n\nContext:\n" + request.context if request.context else "") +
        base_note +
        "\n\nProject rules (AGENTS.md):\n" + rules_text +
        "\n\nDiff to review:\n```diff\n" + diff_text + "\n```\n"
    )

    if client is None:
        client = DeepSeekClient(load_deepseek(), max_retries=0)

    raw = client.chat([
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ], temperature=0.1, max_tokens=16000,
       response_format={"type": "json_object"})

    try:
        result = _parse_response(raw)
    except ReviewParseError:
        # Retry once with a much smaller prompt on parse failure
        small_prompt = (
            "Changed files:\n" + "\n".join(request.changed_files) +
            "\n\nDiff to review (truncated):\n```diff\n" +
            diff_text[:8000] + "\n```\n"
        )
        raw = client.chat([
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": small_prompt},
        ], temperature=0.1, max_tokens=8000,
           response_format={"type": "json_object"})
        result = _parse_response(raw)

    if injected_findings:
        combined = tuple(injected_findings) + result.findings
        if result.verdict == "approve":
            result = ReviewResult(verdict="request_changes",
                                  summary=result.summary, findings=combined)
        else:
            result = ReviewResult(verdict=result.verdict,
                                  summary=result.summary, findings=combined)
    return result
