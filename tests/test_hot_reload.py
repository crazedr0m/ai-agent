# -*- coding: utf-8 -*-
# tests/test_hot_reload.py — Тесты для Hot Reload (Фаза 4.6)

import unittest

from tests import *  # noqa: sys.path


class TestPhase4HotReload(unittest.TestCase):
    """Тесты для Hot Reload (Фаза 4.6)."""

    def test_filepath_to_module(self):
        """_filepath_to_module конвертирует пути."""
        from modules.hot_reload import _filepath_to_module
        import core
        import modules.parser
        self.assertEqual(_filepath_to_module("modules/parser.py"), "modules.parser")
        self.assertEqual(_filepath_to_module("core/core.py"), "core.core")
        self.assertIsNone(_filepath_to_module("nonexistent.py"))

    def test_get_zone_for_file(self):
        """get_zone_for_file определяет зону."""
        from modules.hot_reload import get_zone_for_file
        self.assertEqual(get_zone_for_file("_core.py"), "supervised")
        self.assertEqual(get_zone_for_file("core/core.py"), "supervised")
        self.assertEqual(get_zone_for_file("agents/casual_agent.py"), "autonomous")
        self.assertEqual(get_zone_for_file("modules/tool_parser.py"), "autonomous")
        self.assertEqual(get_zone_for_file("prompts.json"), "autonomous")
        self.assertIsNone(get_zone_for_file("unknown/file.txt"))

    def test_reload_zone_kernel(self):
        """reload_zone('kernel') возвращает пустой словарь."""
        from modules.hot_reload import reload_zone
        result = reload_zone("kernel")
        self.assertEqual(result, {})

    def test_reload_module_not_loaded(self):
        """reload_module для незагруженного модуля возвращает False."""
        from modules.hot_reload import reload_module
        result = reload_module("nonexistent_module_xyz")
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()