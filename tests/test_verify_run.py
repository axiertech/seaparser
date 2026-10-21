"""Offline-tester för scripts/verify_run.py."""
import datetime as dt
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts import verify_run as vr


class ResolveRunTests(unittest.TestCase):
    def _history(self, runs):
        return {"version": 1, "runs": runs}

    def test_resolve_by_run_number_today(self):
        today = dt.date.today().isoformat()
        history = self._history([
            {"run": 1, "date": today},
            {"run": 2, "date": today},
        ])
        entry = vr._resolve_run(history, "2")
        self.assertEqual(entry["run"], 2)

    def test_resolve_by_full_date(self):
        history = self._history([{"run": 3, "date": "2026-10-20"}])
        entry = vr._resolve_run(history, "2026-10-20_3")
        self.assertEqual(entry["run"], 3)

    def test_ambiguous_run_number_requires_date(self):
        history = self._history([
            {"run": 3, "date": "2025-01-01"},
            {"run": 3, "date": "2025-01-02"},
        ])
        with self.assertRaises(SystemExit):
            vr._resolve_run(history, "3")

    def test_missing_run_raises(self):
        with self.assertRaises(SystemExit):
            vr._resolve_run({"version": 1, "runs": []}, "9")

    def test_resolve_run_zero_raises(self):
        """Run 0 ska avvisas med SystemExit."""
        today = dt.date.today().isoformat()
        history = self._history([{"run": 1, "date": today}])
        with self.assertRaises(SystemExit):
            vr._resolve_run(history, "0")

    def test_resolve_negative_run_raises(self):
        """Negativt runnummer ska avvisas med SystemExit."""
        today = dt.date.today().isoformat()
        history = self._history([{"run": 1, "date": today}])
        with self.assertRaises(SystemExit):
            vr._resolve_run(history, "-1")

    def test_resolve_full_date_wrong_run_raises(self):
        """Fullt datum med okänt runnummer ska avvisas med SystemExit."""
        history = self._history([{"run": 3, "date": "2026-10-19"}])
        with self.assertRaises(SystemExit):
            vr._resolve_run(history, "2026-10-19_99")

    def test_resolve_prefers_today_when_ambiguous(self):
        """Vid samma runnummer väljs dagens post framför gårdagens."""
        today = dt.date.today()
        yesterday = today - dt.timedelta(days=1)
        history = self._history([
            {"run": 2, "date": yesterday.isoformat()},
            {"run": 2, "date": today.isoformat()},
        ])
        entry = vr._resolve_run(history, "2")
        self.assertEqual(entry["date"], today.isoformat())


class CheckCompletedTests(unittest.TestCase):
    def test_completed_with_commit_ok(self):
        entry = {"status": "completed", "commit": "a" * 40}
        self.assertTrue(vr._check_completed(entry).ok)

    def test_missing_commit_fails(self):
        entry = {"status": "completed", "commit": None}
        self.assertFalse(vr._check_completed(entry).ok)

    def test_non_completed_fails(self):
        entry = {"status": "failed", "commit": "a" * 40}
        self.assertFalse(vr._check_completed(entry).ok)


class CheckWorktreeTests(unittest.TestCase):
    def test_missing_worktree_fails(self):
        entry = {"worktree": "/nonexistent/xyz"}
        self.assertFalse(vr._check_worktree(entry).ok)

    def test_existing_worktree_ok(self):
        with TemporaryDirectory() as tmp:
            entry = {"worktree": tmp}
            self.assertTrue(vr._check_worktree(entry).ok)


if __name__ == "__main__":
    unittest.main()
