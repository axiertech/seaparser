"""Offline tests for clean_temp_files in infrastructure/deepseek_tools.py."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from infrastructure.deepseek_tools import clean_temp_files


class CleanTempFilesTests(unittest.TestCase):
    """Verify that clean_temp_files removes temp files and keeps regular ones."""

    def test_cleanup_removes_tmp_files(self):
        """Temp files matching TEMP_PATTERNS are removed and reported."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            names = [".tmp_x.py", "y.tmp", "z.bak"]
            for name in names:
                (root / name).write_text("x")
            removed = clean_temp_files(root)
            for name in names:
                self.assertFalse((root / name).exists(), name)
                self.assertIn(name, removed)

    def test_cleanup_leaves_regular_files(self):
        """Regular files are untouched by clean_temp_files."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.py").write_text("x = 1")
            (root / "b.md").write_text("# doc")
            clean_temp_files(root)
            self.assertTrue((root / "a.py").exists())
            self.assertTrue((root / "b.md").exists())

    def test_cleanup_empty_directory(self):
        """An empty directory yields an empty removal list."""
        with TemporaryDirectory() as tmp:
            self.assertEqual(clean_temp_files(Path(tmp)), [])

    def test_cleanup_nested_tmp_files(self):
        """Temp files in subdirectories are found via rglob."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            sub = root / "sub"
            sub.mkdir()
            (sub / ".tmp_x.py").write_text("x")
            removed = clean_temp_files(root)
            self.assertFalse((sub / ".tmp_x.py").exists())
            self.assertIn(str(Path("sub") / ".tmp_x.py"), removed)


if __name__ == "__main__":
    unittest.main()
