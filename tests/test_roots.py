"""Offline tests for infrastructure/roots.py."""
import unittest

from infrastructure.roots import ROOTS, get_root_config


class RootConfigTests(unittest.TestCase):
    def test_both_roots_exist(self):
        self.assertIn("app", ROOTS)
        self.assertIn("autonomy", ROOTS)

    def test_app_root_paths_are_absolute(self):
        cfg = get_root_config("app")
        self.assertTrue(cfg.root.is_absolute())
        self.assertTrue(cfg.task_file.name.endswith("AUTONOMOUS_TASK.md"))
        self.assertTrue(cfg.history_file.name.endswith("RUN_HISTORY.json"))

    def test_autonomy_allows_flat_layout(self):
        cfg = get_root_config("autonomy")
        self.assertIn("", cfg.allowed_prefixes)

    def test_autonomy_forbids_runtime_files(self):
        cfg = get_root_config("autonomy")
        for name in ("handoff.session", "run.lock", "tmux.sock"):
            self.assertIn(name, cfg.forbidden_files)

    def test_worktree_paths_do_not_collide(self):
        app = get_root_config("app")
        autonomy = get_root_config("autonomy")
        self.assertNotEqual(app.worktree_prefix, autonomy.worktree_prefix)
        app_path = app.worktree_path("2026-10-21", 1)
        autonomy_path = autonomy.worktree_path("2026-10-21", 1)
        self.assertNotEqual(app_path, autonomy_path)

    def test_branch_names_do_not_collide(self):
        app = get_root_config("app")
        autonomy = get_root_config("autonomy")
        self.assertNotEqual(app.branch_name("2026-10-21", 1),
                            autonomy.branch_name("2026-10-21", 1))

    def test_unknown_root_raises(self):
        with self.assertRaises(SystemExit):
            get_root_config("nonexistent")


if __name__ == "__main__":
    unittest.main()
