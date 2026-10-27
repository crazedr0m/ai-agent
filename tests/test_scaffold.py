# -*- coding: utf-8 -*-
# tests/test_scaffold.py — Тесты для Scaffold (Фаза 4.5)

import unittest

from tests import *  # noqa: sys.path


class TestPhase4Scaffold(unittest.TestCase):
    """Тесты для Scaffold (Фаза 4.5)."""

    def test_scaffold_tool_template(self):
        """_tool_template генерирует корректный код."""
        from modules.scaffold import Scaffold
        sc = Scaffold()
        template = sc._tool_template("my_tool", "My tool description")
        self.assertIn("my_tool", template)
        self.assertIn("register_tool", template)
        self.assertIn("My tool description", template)

    def test_scaffold_module_template(self):
        """_module_template генерирует корректный код."""
        from modules.scaffold import Scaffold
        sc = Scaffold()
        template = sc._module_template("my_module", "My module")
        self.assertIn("my_module", template)
        self.assertIn("My_module", template)

    def test_scaffold_mcp_template(self):
        """_mcp_server_files генерирует корректный код подпакета."""
        from modules.scaffold import Scaffold
        sc = Scaffold()
        files = sc._mcp_server_files("my_server", "My server")
        self.assertEqual(len(files), 3)
        for fname, content in files:
            self.assertIsInstance(fname, str)
            self.assertIsInstance(content, str)
        self.assertEqual(files[0][0], "__init__.py")
        self.assertIn("my_server", files[0][1])
        self.assertIn("FastMCP", files[1][1])
        self.assertIn("ping", files[2][1])


if __name__ == "__main__":
    unittest.main()