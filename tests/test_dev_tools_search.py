# -*- coding: utf-8 -*-
# tests/test_dev_tools_search.py — Тесты search_code, _search_python

import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import tempfile
import shutil
import subprocess

from tests import *  # noqa: sys.path


class TestSearchCode(unittest.TestCase):
    """Тесты для dev_tools.search_code()."""

    @patch("subprocess.run")
    def test_grep_success(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "file.py:10:def foo()\nfile.py:20:    pass"
        mock_run.return_value = mock_result

        from modules.dev_tools import search_code
        result = search_code("foo", path=".", file_pattern="*.py")
        self.assertIn("file.py:10", result)
        self.assertIn("file.py:20", result)

    @patch("subprocess.run")
    def test_grep_truncates_many_results(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "\n".join([f"f.py:{i}:line" for i in range(150)])
        mock_run.return_value = mock_result

        from modules.dev_tools import search_code
        result = search_code("line")
        self.assertIn("... и ещё", result)

    @patch("subprocess.run")
    def test_grep_no_results(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        from modules.dev_tools import search_code
        result = search_code("nonexistent")
        self.assertEqual(result, "Совпадений не найдено")

    @patch("subprocess.run", side_effect=FileNotFoundError())
    @patch("modules.dev_tools._search_python", return_value="python fallback")
    def test_grep_fallback_to_python(self, mock_search_python, mock_run):
        from modules.dev_tools import search_code
        result = search_code("pattern")
        self.assertEqual(result, "python fallback")

    @patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 30))
    def test_grep_timeout(self, mock_run):
        from modules.dev_tools import search_code
        result = search_code("pattern")
        self.assertIn("таймаут", result)


class TestSearchPythonFallback(unittest.TestCase):
    """Тесты для _search_python() — fallback для grep."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.test_dir, "sub"))
        with open(os.path.join(self.test_dir, "a.py"), "w") as f:
            f.write("def hello():\n    pass\n")
        with open(os.path.join(self.test_dir, "sub", "b.py"), "w") as f:
            f.write("world = 42\n")
        os.makedirs(os.path.join(self.test_dir, "venv"))
        with open(os.path.join(self.test_dir, "venv", "ignored.py"), "w") as f:
            f.write("should not appear")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_find_pattern(self):
        from modules.dev_tools import _search_python
        result = _search_python("hello", self.test_dir, "*.py")
        self.assertIn("hello", result)
        self.assertIn("a.py:", result)

    def test_no_match(self):
        from modules.dev_tools import _search_python
        result = _search_python("nonexistent", self.test_dir, "*.py")
        self.assertEqual(result, "Совпадений не найдено")

    def test_skip_venv(self):
        from modules.dev_tools import _search_python
        result = _search_python("should", self.test_dir, "*.py")
        self.assertNotIn("venv", result)

    def test_skip_non_py(self):
        with open(os.path.join(self.test_dir, "note.txt"), "w") as f:
            f.write("text with hello")
        from modules.dev_tools import _search_python
        result = _search_python("hello", self.test_dir, "*.py")
        self.assertNotIn("note.txt", result)


if __name__ == "__main__":
    unittest.main()