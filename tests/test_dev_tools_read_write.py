# -*- coding: utf-8 -*-
# tests/test_dev_tools_read_write.py — Тесты read_file, write_file, apply_diff

import unittest
from unittest.mock import patch, MagicMock, mock_open

from tests import *  # noqa: sys.path


class TestReadFile(unittest.TestCase):
    """Тесты для dev_tools.read_file()."""

    def test_read_full_file(self):
        m = mock_open(read_data="line1\nline2\nline3\n")
        with patch("builtins.open", m):
            from modules.dev_tools import read_file
            result = read_file("/fake/path.txt")
        self.assertIn("1: line1", result)
        self.assertIn("2: line2", result)
        self.assertIn("3: line3", result)

    def test_read_range(self):
        m = mock_open(read_data="a\nb\nc\nd\ne\n")
        with patch("builtins.open", m):
            from modules.dev_tools import read_file
            result = read_file("/fake/path.txt", start_line=2, end_line=4)
        self.assertIn("2: b", result)
        self.assertNotIn("1: a", result)
        self.assertNotIn("5: e", result)

    def test_read_empty_range(self):
        m = mock_open(read_data="a\nb\n")
        with patch("builtins.open", m):
            from modules.dev_tools import read_file
            result = read_file("/fake/path.txt", start_line=10, end_line=20)
        self.assertIn("пусто", result)

    def test_file_not_found(self):
        from modules.dev_tools import read_file
        result = read_file("/nonexistent/file.txt")
        self.assertIn("не найден", result)

    def test_read_end_line_zero(self):
        m = mock_open(read_data="x\ny\nz\n")
        with patch("builtins.open", m):
            from modules.dev_tools import read_file
            result = read_file("/fake/path.txt", start_line=2, end_line=0)
        self.assertIn("2: y", result)
        self.assertIn("3: z", result)


class TestWriteFile(unittest.TestCase):
    """Тесты для dev_tools.write_file()."""

    @patch("modules.dev_tools.confirm_action", return_value=True)
    def test_write_approved(self, mock_confirm):
        with patch("builtins.open", new_callable=mock_open):
            with patch("os.makedirs"):
                from modules.dev_tools import write_file
                result = write_file("/path/to/file.py", "content here")
        self.assertIn("✅", result)
        self.assertIn("file.py", result)

    @patch("modules.dev_tools.confirm_action", return_value=False)
    def test_write_denied(self, mock_confirm):
        from modules.dev_tools import write_file
        result = write_file("/path/to/file.py", "content")
        self.assertIn("❌", result)

    @patch("modules.dev_tools.confirm_action", return_value=True)
    def test_write_io_error(self, mock_confirm):
        with patch("builtins.open", side_effect=PermissionError("denied")):
            with patch("os.makedirs"):
                from modules.dev_tools import write_file
                result = write_file("/path/to/file.py", "content")
        self.assertIn("Ошибка", result)


class TestApplyDiff(unittest.TestCase):
    """Тесты для dev_tools.apply_diff()."""

    @patch("modules.dev_tools.confirm_action", return_value=True)
    def test_diff_approved(self, mock_confirm):
        m = mock_open(read_data="old text here")
        with patch("builtins.open", m):
            from modules.dev_tools import apply_diff
            result = apply_diff("/f.txt", "old text", "new text")
        self.assertIn("✅", result)

    @patch("modules.dev_tools.confirm_action", return_value=False)
    def test_diff_denied(self, mock_confirm):
        from modules.dev_tools import apply_diff
        result = apply_diff("/f.txt", "old", "new")
        self.assertIn("❌", result)

    @patch("modules.dev_tools.confirm_action", return_value=True)
    def test_diff_string_not_found(self, mock_confirm):
        with patch("builtins.open", mock_open(read_data="different content")):
            from modules.dev_tools import apply_diff
            result = apply_diff("/f.txt", "not there", "new")
        self.assertIn("не найдена", result)

    @patch("modules.dev_tools.confirm_action", return_value=True)
    def test_diff_io_error(self, mock_confirm):
        with patch("builtins.open", side_effect=OSError("oops")):
            from modules.dev_tools import apply_diff
            result = apply_diff("/f.txt", "old", "new")
        self.assertIn("Ошибка", result)


if __name__ == "__main__":
    unittest.main()