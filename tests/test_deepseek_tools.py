"""Offline tests for infrastructure/deepseek_tools.py."""
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from infrastructure.deepseek_tools import (
    execute_tool,
    _find_fuzzy_match,
    _validate_command,
    _validate_path,
)


def _args(**kwargs) -> str:
    """Build a JSON argument string safely, avoiding manual escaping."""
    return json.dumps(kwargs)


class ToolValidationTests(unittest.TestCase):
    def test_path_outside_worktree_rejected(self):
        with TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                _validate_path(Path(tmp), "../outside.py")

    def test_forbidden_file_rejected(self):
        with TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                execute_tool(Path(tmp), "write_file",
                             _args(path="AGENTS.md", content="x"))

    def test_write_and_read_roundtrip(self):
        with TemporaryDirectory() as tmp:
            result = execute_tool(Path(tmp), "write_file",
                                  _args(path="a.py", content="x = 1"))
            self.assertIn("Wrote", result)
            read = execute_tool(Path(tmp), "read_file", _args(path="a.py"))
            self.assertEqual(read, "x = 1")

    def test_disallowed_command_rejected(self):
        with TemporaryDirectory() as tmp:
            result = execute_tool(Path(tmp), "run_command",
                                  _args(command="rm -rf /"))
            self.assertIn("not allowed", result)

    def test_allowed_command_runs(self):
        with TemporaryDirectory() as tmp:
            result = execute_tool(Path(tmp), "run_command",
                                  _args(command="ls"))
            self.assertIn("exit=0", result)

    def test_shell_metacharacters_rejected(self):
        for bad in ("ls; rm x", "ls && rm x", "ls | grep x",
                    "ls > out", "ls $(whoami)", "ls `whoami`"):
            with self.subTest(cmd=bad):
                error = _validate_command(bad)
                self.assertIsNotNone(error)
                self.assertIn("forbidden", error)

    def test_custom_forbidden_files(self):
        with TemporaryDirectory() as tmp:
            custom = frozenset({"handoff.session"})
            with self.assertRaises(ValueError):
                execute_tool(Path(tmp), "write_file",
                             _args(path="handoff.session", content="x"),
                             forbidden_files=custom)
            result = execute_tool(Path(tmp), "write_file",
                                  _args(path="handoff.session", content="x"))
            self.assertIn("Wrote", result)


class WriteFileLimitTests(unittest.TestCase):
    def test_large_file_rejected_by_write_file(self):
        with TemporaryDirectory() as tmp:
            large_content = "x = 1\n" * 1000  # ~6000 bytes
            (Path(tmp) / "big.py").write_text(large_content)
            result = execute_tool(
                Path(tmp), "write_file",
                _args(path="big.py", content=large_content)
            )
            self.assertIn("ERROR", result)
            self.assertIn("use edit_file", result.lower())

    def test_small_file_allowed(self):
        with TemporaryDirectory() as tmp:
            (Path(tmp) / "small.py").write_text("x = 1")
            result = execute_tool(
                Path(tmp), "write_file",
                _args(path="small.py", content="x = 2")
            )
            self.assertIn("Wrote", result)


class EditFileExactTests(unittest.TestCase):
    def test_exact_match_replaces(self):
        with TemporaryDirectory() as tmp:
            (Path(tmp) / "a.py").write_text("def foo():\n    return 1\n")
            result = execute_tool(
                Path(tmp), "edit_file",
                _args(path="a.py",
                      old_string="return 1",
                      new_string="return 2")
            )
            self.assertIn("exact match", result)
            self.assertEqual((Path(tmp) / "a.py").read_text(),
                             "def foo():\n    return 2\n")

    def test_ambiguous_exact_match_rejected(self):
        with TemporaryDirectory() as tmp:
            (Path(tmp) / "a.py").write_text("x = 1\nx = 1\nx = 1\n")
            result = execute_tool(
                Path(tmp), "edit_file",
                _args(path="a.py", old_string="x = 1", new_string="x = 2")
            )
            self.assertIn("matches 3 times", result)

    def test_nonexistent_file_rejected(self):
        with TemporaryDirectory() as tmp:
            result = execute_tool(
                Path(tmp), "edit_file",
                _args(path="missing.py", old_string="x", new_string="y")
            )
            self.assertIn("does not exist", result)


class EditFileFuzzyTests(unittest.TestCase):
    def test_fuzzy_handles_indent_difference(self):
        with TemporaryDirectory() as tmp:
            (Path(tmp) / "a.py").write_text("def foo():\n  return 1\n")
            result = execute_tool(
                Path(tmp), "edit_file",
                _args(path="a.py",
                      old_string="def foo():\n    return 1",
                      new_string="def foo():\n    return 2")
            )
            self.assertIn("fuzzy match", result)
            self.assertEqual((Path(tmp) / "a.py").read_text(),
                             "def foo():\n    return 2\n")

    def test_fuzzy_handles_blank_lines(self):
        with TemporaryDirectory() as tmp:
            (Path(tmp) / "a.py").write_text(
                "import os\n\ndef foo():\n    return 1\n"
            )
            result = execute_tool(
                Path(tmp), "edit_file",
                _args(path="a.py",
                      old_string="import os\ndef foo():\n    return 1",
                      new_string="import os\ndef foo():\n    return 2")
            )
            self.assertIn("fuzzy match", result)

    def test_fuzzy_not_found_returns_clear_error(self):
        with TemporaryDirectory() as tmp:
            (Path(tmp) / "a.py").write_text("def foo():\n    return 1\n")
            result = execute_tool(
                Path(tmp), "edit_file",
                _args(path="a.py",
                      old_string="completely different content",
                      new_string="replacement")
            )
            self.assertIn("not found", result)
            self.assertIn("exact and fuzzy", result)

    def test_find_fuzzy_match_direct(self):
        text = "line one\nline two\nline three\nline four"
        match = _find_fuzzy_match(text, "line one\nline  two\nline three")
        self.assertIsNotNone(match)
        start, end, ratio = match
        self.assertEqual(start, 0)
        self.assertEqual(end, 3)
        self.assertGreaterEqual(ratio, 0.85)

    def test_find_fuzzy_match_skips_blank_lines(self):
        text = "a\n\nb\n\nc"
        match = _find_fuzzy_match(text, "a\nb\nc")
        self.assertIsNotNone(match)
        start, end, _ = match
        self.assertEqual(start, 0)
        self.assertEqual(end, 5)

    def test_fuzzy_empty_old_string(self):
        """An empty old_string must return None instead of crashing."""
        with TemporaryDirectory() as tmp:
            (Path(tmp) / "a.py").write_text("x = 1\n")
            text = (Path(tmp) / "a.py").read_text()
            self.assertIsNone(_find_fuzzy_match(text, ""))

    def test_fuzzy_whitespace_only_old_string(self):
        """A whitespace-only old_string must return None, not a match."""
        with TemporaryDirectory() as tmp:
            (Path(tmp) / "a.py").write_text("x = 1\n")
            text = (Path(tmp) / "a.py").read_text()
            self.assertIsNone(_find_fuzzy_match(text, "   "))

    def test_fuzzy_single_line_file(self):
        """A single-line file must be editable via exact or fuzzy match."""
        with TemporaryDirectory() as tmp:
            (Path(tmp) / "a.py").write_text("x = 1\n")
            result = execute_tool(
                Path(tmp), "edit_file",
                _args(path="a.py", old_string="x = 1", new_string="x = 2")
            )
            self.assertIn("Edited a.py", result)
            self.assertEqual((Path(tmp) / "a.py").read_text(), "x = 2\n")

    def test_fuzzy_no_match_returns_none(self):
        """Unrelated old_string must yield None from _find_fuzzy_match."""
        with TemporaryDirectory() as tmp:
            (Path(tmp) / "a.py").write_text("def foo():\n    return 1\n")
            text = (Path(tmp) / "a.py").read_text()
            self.assertIsNone(
                _find_fuzzy_match(text, "zzz qqq totally unrelated content")
            )

    def test_fuzzy_identical_files_match_at_line_zero(self):
        """Identical file and old_string must match starting at line 0."""
        with TemporaryDirectory() as tmp:
            content = "def foo():\n    return 1\n"
            (Path(tmp) / "a.py").write_text(content)
            text = (Path(tmp) / "a.py").read_text()
            match = _find_fuzzy_match(text, content)
            self.assertIsNotNone(match)
            start, _, ratio = match
            self.assertEqual(start, 0)
            self.assertGreaterEqual(ratio, 0.85)


if __name__ == "__main__":
    unittest.main()
