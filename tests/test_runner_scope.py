"""Tests for the scope enforcement helpers in scripts.runner."""
import unittest

from scripts.runner import _allowed_files_for_task, _check_scope


class AllowedFilesForTaskTests(unittest.TestCase):
    def test_no_allowed_line_returns_none(self):
        task = "Model: deepseek-flash\n\nDo the thing."
        self.assertIsNone(_allowed_files_for_task(task))

    def test_single_file(self):
        task = "Allowed files: docs/runner.md"
        self.assertEqual(_allowed_files_for_task(task),
                         frozenset({"docs/runner.md"}))

    def test_multiple_files_trimmed(self):
        task = "Allowed files: a.py, b.py,  c.py "
        self.assertEqual(_allowed_files_for_task(task),
                         frozenset({"a.py", "b.py", "c.py"}))

    def test_case_insensitive_key(self):
        task = "allowed files: x.py"
        self.assertEqual(_allowed_files_for_task(task),
                         frozenset({"x.py"}))


class CheckScopeTests(unittest.TestCase):
    def test_no_allowlist_always_ok(self):
        self.assertIsNone(_check_scope(["any.py"], None))

    def test_exact_match_ok(self):
        self.assertIsNone(_check_scope(["a.py"], frozenset({"a.py"})))

    def test_extra_file_rejected(self):
        result = _check_scope(["a.py", "b.py"], frozenset({"a.py"}))
        self.assertIsNotNone(result)
        self.assertIn("SCOPE VIOLATION", result)
        self.assertIn("b.py", result)
        self.assertNotIn("a.py,", result)  # only the extra file listed

    def test_empty_written_ok(self):
        self.assertIsNone(_check_scope([], frozenset({"a.py"})))


if __name__ == "__main__":
    unittest.main()
