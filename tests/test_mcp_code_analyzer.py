# -*- coding: utf-8 -*-
# tests/test_mcp_code_analyzer.py — Контрактные тесты для Code Analyzer MCP-сервера

import unittest
import os
import tempfile
import shutil
import json

from tests import *  # noqa: sys.path


class TestMCPServerCodeAnalyzer(unittest.TestCase):
    """Контрактные тесты для Code Analyzer MCP-сервера (Фаза 5.2)."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.tmpdir)

        # Создаём тестовый проект
        os.makedirs("mypkg", exist_ok=True)

        with open("mypkg/__init__.py", "w") as f:
            f.write("# package\n")

        with open("mypkg/utils.py", "w") as f:
            f.write("""
def add(a: int, b: int) -> int:
    \"\"\"Add two numbers.\"\"\"
    return a + b


def multiply(a: int, b: int) -> int:
    \"\"\"Multiply two numbers.\"\"\"
    return add(a, b) * 0  # calls add
""")

        with open("mypkg/main.py", "w") as f:
            f.write("""
from mypkg.utils import add, multiply


class Calculator:
    \"\"\"A simple calculator.\"\"\"

    def compute(self, x: int, y: int) -> int:
        return add(x, y)


def run():
    calc = Calculator()
    result = calc.compute(1, 2)
    print(result)
""")

    def tearDown(self):
        os.chdir(self.old_cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _reset_cache(self):
        """Сбросить кэш AST через прямой вызов."""
        from mcp_servers.code_analyzer.tools import _clear_cache
        _clear_cache()

    def test_scan_project(self):
        """scan_project возвращает сводку по проекту."""
        from mcp_servers.code_analyzer.tools import scan_project
        result = scan_project(".")
        data = json.loads(result)
        self.assertIn("summary", data)
        self.assertIn("files_scanned", data["summary"])
        self.assertGreaterEqual(data["summary"]["files_scanned"], 3)
        self.assertIn("functions", data)
        self.assertIn("classes", data)

    def test_scan_project_contains_functions(self):
        """scan_project находит функции."""
        from mcp_servers.code_analyzer.tools import scan_project
        result = scan_project(".")
        data = json.loads(result)
        func_names = [f["name"] for f in data["functions"]]
        self.assertIn("add", func_names)
        self.assertIn("multiply", func_names)
        self.assertIn("run", func_names)

    def test_scan_project_contains_classes(self):
        """scan_project находит классы."""
        from mcp_servers.code_analyzer.tools import scan_project
        result = scan_project(".")
        data = json.loads(result)
        class_names = [c["name"] for c in data["classes"]]
        self.assertIn("Calculator", class_names)

    def test_scan_project_call_graph(self):
        """scan_project строит граф вызовов."""
        from mcp_servers.code_analyzer.tools import scan_project
        result = scan_project(".")
        data = json.loads(result)
        self.assertIn("call_graph", data)

    def test_scan_project_not_found(self):
        """scan_project возвращает ошибку для несуществующей папки."""
        from mcp_servers.code_analyzer.tools import scan_project
        result = scan_project("/nonexistent/path")
        self.assertIn("не найдена", result)

    def test_query_function(self):
        """query_function возвращает сигнатуру функции."""
        self._reset_cache()
        from mcp_servers.code_analyzer.tools import query_function
        fp = os.path.join(self.tmpdir, "mypkg", "utils.py")
        result = query_function(fp, "add")
        data = json.loads(result)
        self.assertIn("signature", data)
        sig = data["signature"]
        self.assertEqual(sig["name"], "add")
        self.assertEqual(len(sig["params"]), 2)
        self.assertEqual(sig["params"][0]["name"], "a")
        self.assertEqual(sig["params"][0]["type"], "int")
        self.assertEqual(sig["return_type"], "int")

    def test_query_function_not_found(self):
        """query_function возвращает ошибку для несуществующей функции."""
        self._reset_cache()
        from mcp_servers.code_analyzer.tools import query_function
        fp = os.path.join(self.tmpdir, "mypkg", "utils.py")
        result = query_function(fp, "nonexistent")
        self.assertIn("не найдена", result)

    def test_query_callers(self):
        """query_callers показывает, кто вызывает функцию."""
        self._reset_cache()
        from mcp_servers.code_analyzer.tools import query_callers
        fp = os.path.join(self.tmpdir, "mypkg", "utils.py")
        result = query_callers(fp, "add")
        data = json.loads(result)
        self.assertIn("callers", data)
        self.assertIn("multiply", data["callers"])

    def test_query_callees(self):
        """query_callees показывает, кого вызывает функция."""
        self._reset_cache()
        from mcp_servers.code_analyzer.tools import query_callees
        fp = os.path.join(self.tmpdir, "mypkg", "utils.py")
        result = query_callees(fp, "multiply")
        data = json.loads(result)
        self.assertIn("callees", data)
        self.assertIn("add", data["callees"])

    def test_query_callees_empty(self):
        """query_callees для функции без вызовов."""
        self._reset_cache()
        from mcp_servers.code_analyzer.tools import query_callees
        fp = os.path.join(self.tmpdir, "mypkg", "utils.py")
        result = query_callees(fp, "add")
        self.assertIn("ничего не вызывает", result)


if __name__ == "__main__":
    unittest.main()