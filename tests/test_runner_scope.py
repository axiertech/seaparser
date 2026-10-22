"""Offline tests for the scope helpers in scripts/runner.py.

The helpers are pure functions, so no mocking or worktree is needed.
scripts/runner.py imports the DeepSeek client (which needs the optional
`openai` package), so the module is loaded from source with stubbed
dependencies when the real import is unavailable.
"""
import importlib.util
import sys
import types
import unittest
from pathlib import Path

RUNNER_PATH = Path(__file__).resolve().parent.parent / "scripts" / "runner.py"


def _stub_runner_dependencies() -> None:
    """Install minimal stand-ins for runner.py's heavy imports."""
    review_mod = types.ModuleType("application.deepseek_review")
    review_mod.ReviewFinding = type("ReviewFinding", (), {})
    review_mod.ReviewRequest = type("ReviewRequest", (), {})
    review_mod.ReviewResult = type("ReviewResult", (), {})
    review_mod.review = lambda *args, **kwargs: None

    deepseek_mod = types.ModuleType("infrastructure.deepseek")
    deepseek_mod.DeepSeekClient = type("DeepSeekClient", (), {})
    deepseek_mod.DeepSeekError = type("DeepSeekError", (Exception,), {})

    tools_mod = types.ModuleType("infrastructure.deepseek_tools")
    tools_mod.TOOLS = ()
    tools_mod.clean_temp_files = lambda *args, **kwargs: []
    tools_mod.execute_tool = lambda *args, **kwargs: ""

    roots_mod = types.ModuleType("infrastructure.roots")
    roots_mod.RootConfig = type("RootConfig", (), {})
    roots_mod.get_root_config = lambda *args, **kwargs: None

    settings_mod = types.ModuleType("infrastructure.settings")
    settings_mod.DEEPSEEK_DEFAULT_MODEL = "deepseek-flash"
    settings_mod.DEEPSEEK_STRONG_MODEL = "deepseek-pro"
    settings_mod.load_deepseek = lambda *args, **kwargs: None

    for name, module in (
        ("application.deepseek_review", review_mod),
        ("infrastructure.deepseek", deepseek_mod),
        ("infrastructure.deepseek_tools", tools_mod),
        ("infrastructure.roots", roots_mod),
        ("infrastructure.settings", settings_mod),
    ):
        sys.modules.setdefault(name, module)


def _load_runner_module() -> types.ModuleType:
    """Import scripts.runner, stubbing dependencies if the import fails."""
    try:
        import scripts.runner as runner
        return runner
    except ImportError:
        _stub_runner_dependencies()
        import importlib.util

        spec = importlib.util.spec_from_file_location("_runner_scope_under_test",
                                                      RUNNER_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


_runner = _load_runner_module()
_allowed_files_for_task = _runner._allowed_files_for_task
_check_scope = _runner._check_scope


class AllowedFilesForTaskTests(unittest.TestCase):
    def test_missing_line_returns_none(self):
        """A task without an 'Allowed files:' line has no restriction."""
        task = "Fix the bug in application/foo.py.\nNo scope line here.\n"
        self.assertIsNone(_allowed_files_for_task(task))

    def test_comma_separated_list_returns_frozenset(self):
        """A comma-separated list becomes a frozenset of paths."""
        task = "Do the work.\nAllowed files: a, b, c\n"
        self.assertEqual(_allowed_files_for_task(task),
                         frozenset({"a", "b", "c"}))

    def test_whitespace_is_trimmed(self):
        """Surrounding whitespace around each path is stripped."""
        task = "Allowed files:   tests/a.py ,  tests/b.py  \n"
        self.assertEqual(_allowed_files_for_task(task),
                         frozenset({"tests/a.py", "tests/b.py"}))

    def test_single_file(self):
        """A single allowed file yields a one-element frozenset."""
        task = "Allowed files: tests/test_runner_scope.py"
        self.assertEqual(_allowed_files_for_task(task),
                         frozenset({"tests/test_runner_scope.py"}))


class CheckScopeTests(unittest.TestCase):
    def test_written_equal_allowed_returns_none(self):
        """Writing exactly the allowed files is in scope."""
        allowed = frozenset({"a.py", "b.py"})
        self.assertIsNone(_check_scope(["a.py", "b.py"], allowed))

    def test_subset_of_allowed_returns_none(self):
        """Writing fewer files than allowed is in scope."""
        allowed = frozenset({"a.py", "b.py"})
        self.assertIsNone(_check_scope(["a.py"], allowed))

    def test_extra_file_reports_violation(self):
        """An extra file yields a SCOPE VIOLATION naming that file."""
        allowed = frozenset({"a.py"})
        error = _check_scope(["a.py", "extra.py"], allowed)
        self.assertIsNotNone(error)
        self.assertIn("SCOPE VIOLATION", error)
        self.assertIn("extra.py", error)

    def test_none_allowed_permits_anything(self):
        """Without an allowlist any written file is permitted."""
        self.assertIsNone(_check_scope(["anything.py", "else.md"], None))

    def test_none_allowed_with_empty_written(self):
        """No allowlist and no writes is still in scope."""
        self.assertIsNone(_check_scope([], None))


if __name__ == "__main__":
    unittest.main()
