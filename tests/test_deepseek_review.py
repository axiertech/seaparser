"""Databasfria tester för DeepSeek-granskning. Inga nätverksanrop."""
import json
import unittest

from application.deepseek_review import (
    MAX_DIFF_CHARS,
    ReviewFinding,
    ReviewParseError,
    ReviewRequest,
    ReviewResult,
    review,
)
from infrastructure.deepseek import DeepSeekError


def _make_client(response_text=None, error=None):
    calls = []

    class _FakeDeepSeekClient:
        def chat(self, messages, *, temperature=0.2, max_tokens=None):
            calls.append({"messages": messages,
                          "temperature": temperature,
                          "max_tokens": max_tokens})
            if error is not None:
                raise error
            return response_text

    return _FakeDeepSeekClient(), calls


def _valid_response(verdict="approve", findings=None):
    return json.dumps({
        "verdict": verdict,
        "summary": "Ser bra ut.",
        "findings": findings or [],
    })


class ReviewTests(unittest.TestCase):
    def _request(self, diff="--- a/x\n+++ b/x\n+hej\n"):
        return ReviewRequest(diff=diff, agents_rules="Regler.", changed_files=("x.py",))

    def test_empty_diff_does_not_call_client(self):
        client, calls = _make_client()
        result = review(self._request(diff="   \n"), client=client)
        self.assertEqual(result.verdict, "approve")
        self.assertEqual(calls, [])

    def test_parses_valid_response(self):
        client, _ = _make_client(_valid_response("approve"))
        result = review(self._request(), client=client)
        self.assertEqual(result.verdict, "approve")
        self.assertEqual(result.findings, ())

    def test_rejects_invalid_json(self):
        client, _ = _make_client("inte json")
        with self.assertRaises(ReviewParseError):
            review(self._request(), client=client)

    def test_blocker_cannot_be_approve(self):
        client, _ = _make_client(json.dumps({
            "verdict": "approve",
            "summary": "ok",
            "findings": [{"file": "x.py", "line": 1,
                          "severity": "blocker", "message": "fel"}],
        }))
        with self.assertRaises(ReviewParseError):
            review(self._request(), client=client)

    def test_secret_like_content_adds_blocker(self):
        client, _ = _make_client(_valid_response("approve"))
        diff = "--- a/x\n+++ b/x\n+KEY=sk-abcdefghij1234567890\n"
        result = review(self._request(diff=diff), client=client)
        self.assertEqual(result.verdict, "request_changes")
        self.assertTrue(any(f.severity == "blocker" for f in result.findings))

    def test_truncates_long_diff(self):
        client, calls = _make_client(_valid_response("approve"))
        big = "a" * (MAX_DIFF_CHARS + 100)
        result = review(self._request(diff=big), client=client)
        self.assertTrue(any("trunkerades" in f.message for f in result.findings))
        sent = calls[0]["messages"][1]["content"]
        self.assertIn("[trunkerad]", sent)

    def test_propagates_client_error(self):
        client, _ = _make_client(error=DeepSeekError("nätverk"))
        with self.assertRaises(DeepSeekError):
            review(self._request(), client=client)

    def test_reject_with_blocker_finding_returned(self):
        client, _ = _make_client(json.dumps({
            "verdict": "reject",
            "summary": "Diffen bryter mot en absolut regel.",
            "findings": [{
                "file": "x.py",
                "line": 1,
                "severity": "blocker",
                "message": "Hemlighet i diffen.",
                "suggestion": "Ta bort hemligheten.",
            }],
        }))
        result = review(self._request(), client=client)
        self.assertEqual(result.verdict, "reject")
        self.assertTrue(any(f.severity == "blocker" for f in result.findings))


if __name__ == "__main__":
    unittest.main()
