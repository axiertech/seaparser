"""Tests for the scope enforcement helpers in infrastructure.safety."""
import unittest

from infrastructure.safety import allowed_files_for_task, check_scope


class AllowedFilesForTaskTests(unittest.TestCase):
    """Verify parsing of the 'Allowed files:' line."""

    def test_no_allowed_line_returns_none(self):
        """A task without 'Allowed files:' returns None (no restriction)."""
        task = "Model: deepseek-flash\n\nDo the thing."
        self.assertIsNone(allowed_files_for_task(task))

    def test_single_file(self):
        """A single allowed file is parsed correctly."""
        task = "Allowed files: docs/runner.md"
        self.assertEqual(allowed_files_for_task(task),
                         frozenset({"docs/runner.md"}))

    def test_multiple_files_trimmed(self):
        """Multiple files are split and whitespace-trimmed."""
        task = "Allowed files: a.py, b.py,  c.py "
        self.assertEqual(allowed_files_for_task(task),
                         frozenset({"a.py", "b.py", "c.py"}))

    def test_case_insensitive_key(self):
        """The key 'allowed files:' is matched case-insensitively."""
        task = "allowed files: x.py"
        self.assertEqual(allowed_files_for_task(task),
                         frozenset({"x.py"}))


class CheckScopeTests(unittest.TestCase):
    """Verify that written files are checked against the allowlist."""

    def test_none_allowed_permits_anything(self):
        """No allowlist means any written file is permitted."""
        self.assertIsNone(check_scope(["any.py"], None))

    def test_written_equal_allowed_returns_none(self):
        """Writing exactly the allowed files is in scope."""
        self.assertIsNone(check_scope(["a.py"], frozenset({"a.py"})))

    def test_extra_file_reports_violation(self):
        """An extra file yields a SCOPE VIOLATION naming that file."""
        result = check_scope(["a.py", "b.py"], frozenset({"a.py"}))
        self.assertIsNotNone(result)
        self.assertIn("SCOPE VIOLATION", result)
        self.assertIn("b.py", result)
        self.assertNotIn("a.py,", result)  # only the extra file listed

    def test_empty_written_returns_none(self):
        """No writes means no scope violation."""
        self.assertIsNone(check_scope([], frozenset({"a.py"})))

    def test_directory_prefix_allowed(self):
        """A directory prefix allows any file under that directory."""
        allowed = frozenset({"frontend/map/"})
        self.assertIsNone(check_scope(["frontend/map/map.js"], allowed))
        self.assertIsNone(check_scope(["frontend/map/sub/foo.js"], allowed))

    def test_directory_prefix_blocks_outside(self):
        """Files outside the directory prefix are blocked."""
        allowed = frozenset({"frontend/map/"})
        result = check_scope(["frontend/src/Timeline.jsx"], allowed)
        self.assertIsNotNone(result)
        self.assertIn("frontend/src/Timeline.jsx", result)


if __name__ == "__main__":
    unittest.main()
