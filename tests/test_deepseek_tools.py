"""Offline-tester för infrastructure/deepseek_tools.py."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from infrastructure.deepseek_tools import execute_tool, _validate_path


class ToolValidationTests(unittest.TestCase):
    def test_path_outside_worktree_rejected(self):
        with TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                _validate_path(Path(tmp), "../outside.py")

    def test_forbidden_file_rejected(self):
        with TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                execute_tool(Path(tmp), "write_file",
                             '{"path": "AGENTS.md", "content": "x"}')

    def test_write_and_read_roundtrip(self):
        with TemporaryDirectory() as tmp:
            result = execute_tool(Path(tmp), "write_file",
                                  '{"path": "a.py", "content": "x = 1"}')
            self.assertIn("Skrev", result)
            read = execute_tool(Path(tmp), "read_file", '{"path": "a.py"}')
            self.assertEqual(read, "x = 1")

    def test_disallowed_command_rejected(self):
        with TemporaryDirectory() as tmp:
            result = execute_tool(Path(tmp), "run_command",
                                  '{"command": "rm -rf /"}')
            self.assertIn("inte tillåtet", result)

    def test_allowed_command_runs(self):
        with TemporaryDirectory() as tmp:
            result = execute_tool(Path(tmp), "run_command",
                                  '{"command": "ls"}')
            self.assertIn("exit=0", result)


if __name__ == "__main__":
    unittest.main()
