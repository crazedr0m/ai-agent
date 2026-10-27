# -*- coding: utf-8 -*-
# tests/test_tool_registry.py — Тесты для ToolRegistry и интеграции инструментов
#
# Классы:
#   TestToolRegistry        — регистрация/получение/список инструментов
#   TestToolsIntegration    — интеграционные тесты core_tools

import unittest
import os

from tests import *  # noqa: sys.path


class TestToolRegistry(unittest.TestCase):
    """Тесты для ToolRegistry и @register_tool."""

    def test_tool_registry_register_and_get(self):
        """Регистрация и получение инструмента."""
        from core.core_tools import ToolRegistry

        registry = ToolRegistry()

        @registry.register("my_tool", "My test tool")
        def my_tool(arg: str) -> str:
            return f"processed: {arg}"

        func = registry.get("my_tool")
        self.assertIsNotNone(func)
        self.assertEqual(func("input"), "processed: input")

    def test_tool_registry_decorator(self):
        """Декоратор @register_tool работает."""
        from core.core_tools import ToolRegistry

        registry = ToolRegistry()

        @registry.register("calc", "Calculator")
        def calc(x: str) -> str:
            return str(int(x) * 2)

        self.assertIn("calc", registry)
        self.assertEqual(registry.get("calc")("5"), "10")

    def test_tool_registry_list_tools(self):
        """list_tools возвращает описание."""
        from core.core_tools import ToolRegistry

        registry = ToolRegistry()

        @registry.register("a", "Tool A")
        def tool_a(x): return x

        @registry.register("b", "Tool B")
        def tool_b(x): return x

        listing = registry.list_tools()
        self.assertIn("a", listing)
        self.assertIn("Tool A", listing)
        self.assertIn("b", listing)
        self.assertIn("Tool B", listing)

    def test_tool_registry_len_contains(self):
        """__len__ и __contains__ работают."""
        from core.core_tools import ToolRegistry

        registry = ToolRegistry()
        self.assertEqual(len(registry), 0)

        @registry.register("x", "X")
        def tool_x(x): return x

        self.assertEqual(len(registry), 1)
        self.assertIn("x", registry)
        self.assertNotIn("y", registry)


class TestToolsIntegration(unittest.TestCase):
    """Интеграционные тесты инструментов (без LLM)."""

    def test_list_dir(self):
        """list_dir возвращает содержимое папки."""
        import core_tools
        result = core_tools.list_dir(".")
        self.assertIn("core_tools.py", result)

    def test_view_file_outline(self):
        """view_file_outline показывает сигнатуры."""
        import core_tools
        result = core_tools.view_file_outline("core_tools.py")
        self.assertIn("def ", result)

    def test_read_file_chunk(self):
        """read_file_chunk читает диапазон строк."""
        import core_tools
        result = core_tools.read_file_chunk("test_core.py", 16, 18)
        self.assertIn("import", result)

    def test_tools_registered_via_decorator(self):
        """Инструменты зарегистрированы через @register_tool."""
        from core.core_tools import _GLOBAL_REGISTRY
        import core_tools  # noqa: регистрирует инструменты

        for name in ["list_dir", "view_file_outline",
                     "read_file_chunk", "query_db_schema"]:
            self.assertIn(name, _GLOBAL_REGISTRY,
                          f"{name} не зарегистрирован")


if __name__ == "__main__":
    unittest.main()