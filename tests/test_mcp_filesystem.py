# -*- coding: utf-8 -*-
# tests/test_mcp_filesystem.py — Контрактные тесты для Filesystem MCP-сервера

import unittest
import os
import tempfile
import shutil

from tests import *  # noqa: sys.path


class TestMCPServerFilesystem(unittest.TestCase):
    """Контрактные тесты для Filesystem MCP-сервера (Фаза 3.4)."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.tmpdir)

        with open("test.txt", "w") as f:
            f.write("line1\nline2\nline3\n")
        os.makedirs("subdir", exist_ok=True)
        with open("subdir/nested.py", "w") as f:
            f.write("def hello():\n    pass\n")

    def tearDown(self):
        os.chdir(self.old_cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_list_dir(self):
        """list_dir показывает содержимое папки."""
        from mcp_servers.filesystem.tools import list_dir
        result = list_dir(".")
        self.assertIn("test.txt", result)
        self.assertIn("subdir/", result)

    def test_read_file(self):
        """read_file читает файл."""
        from mcp_servers.filesystem.tools import read_file
        result = read_file("test.txt")
        self.assertIn("line1", result)
        self.assertIn("line3", result)

    def test_read_file_range(self):
        """read_file с диапазоном строк."""
        from mcp_servers.filesystem.tools import read_file
        result = read_file("test.txt", start_line=2, end_line=2)
        self.assertIn("line2", result)
        self.assertNotIn("line1", result)

    def test_read_file_not_found(self):
        """read_file возвращает ошибку для несуществующего файла."""
        from mcp_servers.filesystem.tools import read_file
        result = read_file("nonexistent.txt")
        self.assertIn("не найден", result)

    def test_write_file(self):
        """write_file создаёт файл."""
        from mcp_servers.filesystem.tools import write_file
        result = write_file("new.txt", "hello world")
        self.assertIn("записан", result)
        self.assertTrue(os.path.exists("new.txt"))
        with open("new.txt") as f:
            self.assertEqual(f.read(), "hello world")

    def test_search_files(self):
        """search_files находит файлы по glob."""
        from mcp_servers.filesystem.tools import search_files
        result = search_files("*.txt")
        self.assertIn("test.txt", result)

    def test_stat_file(self):
        """stat_file показывает информацию о файле."""
        from mcp_servers.filesystem.tools import stat_file
        result = stat_file("test.txt")
        self.assertIn("Файл", result)
        self.assertIn("Размер", result)

    def test_grep_code(self):
        """grep_code находит строки по regex."""
        from mcp_servers.filesystem.tools import grep_code
        result = grep_code("line[12]", ".", file_pattern="*.txt")
        self.assertIn("test.txt", result)
        self.assertIn("line1", result)
        self.assertIn("line2", result)
        self.assertNotIn("line3", result)


if __name__ == "__main__":
    unittest.main()