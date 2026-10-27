# -*- coding: utf-8 -*-
# tests/test_repo_map.py — Тесты для modules/repo_map.py

import os
import sys
import tempfile
import unittest

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.repo_map import build_repo_map, format_repo_map_for_llm, format_dependency_map


class TestBuildRepoMap(unittest.TestCase):
    """Тесты для build_repo_map()."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        # Создаём тестовые файлы
        with open(os.path.join(self.tmpdir, "main.py"), "w") as f:
            f.write("import utils\n\ndef main():\n    utils.hello()\n")
        with open(os.path.join(self.tmpdir, "utils.py"), "w") as f:
            f.write("def hello():\n    print('hello')\n")
        with open(os.path.join(self.tmpdir, "models.py"), "w") as f:
            f.write("class User:\n    pass\n\nclass Admin(User):\n    pass\n")

    def test_build_repo_map_returns_dict(self):
        result = build_repo_map(self.tmpdir)
        self.assertIsInstance(result, dict)

    def test_build_repo_map_summary(self):
        result = build_repo_map(self.tmpdir)
        s = result.get("summary", {})
        self.assertEqual(s.get("files_scanned"), 3)
        self.assertGreater(s.get("total_functions", 0), 0)

    def test_build_repo_map_file_summary(self):
        result = build_repo_map(self.tmpdir)
        fs = result.get("file_summary", {})
        self.assertIn("main.py", fs)
        self.assertIn("utils.py", fs)
        self.assertIn("models.py", fs)

    def test_format_repo_map_for_llm(self):
        result = build_repo_map(self.tmpdir)
        text = format_repo_map_for_llm(result)
        self.assertIsInstance(text, str)
        self.assertIn("Проект:", text)

    def test_format_dependency_map(self):
        result = build_repo_map(self.tmpdir)
        text = format_dependency_map(result)
        self.assertIsInstance(text, str)

    def test_build_repo_map_error(self):
        result = build_repo_map("/nonexistent/path")
        self.assertIn("error", result)

    def test_skip_dirs(self):
        skip_dir = os.path.join(self.tmpdir, "venv")
        os.makedirs(skip_dir)
        with open(os.path.join(skip_dir, "ignored.py"), "w") as f:
            f.write("# ignored\n")
        result = build_repo_map(self.tmpdir, skip_dirs=["venv"])
        self.assertEqual(result["summary"]["files_scanned"], 3)


if __name__ == "__main__":
    unittest.main()