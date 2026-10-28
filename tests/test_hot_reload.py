# -*- coding: utf-8 -*-
# tests/test_hot_reload.py — Тесты для Hot Reload (Фаза 4.6)

import unittest
import unittest.mock
import sys

from tests import *  # noqa: sys.path


class TestFilePathToModule(unittest.TestCase):
    """_filepath_to_module."""

    def test_normal_path(self):
        from modules.hot_reload import _filepath_to_module
        import modules.parser
        self.assertEqual(_filepath_to_module("modules/parser.py"), "modules.parser")

    def test_core_path(self):
        from modules.hot_reload import _filepath_to_module
        import core.core
        self.assertEqual(_filepath_to_module("core/core.py"), "core.core")

    def test_nonexistent_returns_none(self):
        from modules.hot_reload import _filepath_to_module
        self.assertIsNone(_filepath_to_module("nonexistent.py"))

    def test_strip_dot_slash(self):
        from modules.hot_reload import _filepath_to_module
        import modules.tracer
        self.assertEqual(_filepath_to_module("./modules/tracer.py"), "modules.tracer")

    def test_init_path(self):
        from modules.hot_reload import _filepath_to_module
        import core
        self.assertEqual(_filepath_to_module("core/__init__.py"), "core")

    def test_windows_backslash(self):
        from modules.hot_reload import _filepath_to_module
        import modules.parser
        self.assertEqual(_filepath_to_module("modules\\parser.py"), "modules.parser")


class TestGetZoneForFile(unittest.TestCase):
    """get_zone_for_file."""

    def test_supervised_core(self):
        from modules.hot_reload import get_zone_for_file
        self.assertEqual(get_zone_for_file("core/runtime.py"), "supervised")

    def test_supervised_core_path(self):
        from modules.hot_reload import get_zone_for_file
        self.assertEqual(get_zone_for_file("core/core.py"), "supervised")

    def test_autonomous_agents(self):
        from modules.hot_reload import get_zone_for_file
        self.assertEqual(get_zone_for_file("agents/casual_agent.py"), "autonomous")

    def test_autonomous_modules(self):
        from modules.hot_reload import get_zone_for_file
        self.assertEqual(get_zone_for_file("modules/tool_parser.py"), "autonomous")

    def test_autonomous_prompts_json(self):
        from modules.hot_reload import get_zone_for_file
        self.assertEqual(get_zone_for_file("prompts.json"), "autonomous")

    def test_autonomous_prompts_dir(self):
        from modules.hot_reload import get_zone_for_file
        self.assertEqual(get_zone_for_file("prompts/coder_developer.txt"), "autonomous")

    def test_autonomous_core_tools_root(self):
        from modules.hot_reload import get_zone_for_file
        self.assertEqual(get_zone_for_file("core_tools.py"), "autonomous")

    def test_autonomous_mcp_servers(self):
        from modules.hot_reload import get_zone_for_file
        self.assertEqual(get_zone_for_file("mcp_servers/fetch/tools.py"), "autonomous")

    def test_unknown_returns_none(self):
        from modules.hot_reload import get_zone_for_file
        self.assertIsNone(get_zone_for_file("unknown/file.txt"))

    def test_unknown_other_ext(self):
        from modules.hot_reload import get_zone_for_file
        self.assertIsNone(get_zone_for_file("docs/readme.md"))


class TestReloadModule(unittest.TestCase):
    """reload_module."""

    def test_unloaded_module_returns_false(self):
        from modules.hot_reload import reload_module
        result = reload_module("nonexistent_module_xyz")
        self.assertFalse(result)

    @unittest.mock.patch("modules.hot_reload.importlib.reload")
    def test_loaded_module_returns_true(self, mock_reload):
        from modules.hot_reload import reload_module
        sys.modules["test_dummy_mod"] = unittest.mock.MagicMock()
        try:
            result = reload_module("test_dummy_mod")
            self.assertTrue(result)
            mock_reload.assert_called_once()
        finally:
            sys.modules.pop("test_dummy_mod", None)

    @unittest.mock.patch("modules.hot_reload.importlib.reload",
                          side_effect=ImportError("fail"))
    def test_reload_exception_returns_false(self, mock_reload):
        from modules.hot_reload import reload_module
        sys.modules["test_bad_mod"] = unittest.mock.MagicMock()
        try:
            result = reload_module("test_bad_mod")
            self.assertFalse(result)
        finally:
            sys.modules.pop("test_bad_mod", None)


class TestReloadZone(unittest.TestCase):
    """reload_zone."""

    def test_kernel_returns_empty(self):
        from modules.hot_reload import reload_zone
        result = reload_zone("kernel")
        self.assertEqual(result, {})

    @unittest.mock.patch("modules.hot_reload.reload_module")
    def test_unknown_zone_returns_empty(self, mock_reload):
        from modules.hot_reload import reload_zone
        result = reload_zone("nonexistent_zone")
        self.assertEqual(result, {})

    @unittest.mock.patch("modules.hot_reload.reload_module", return_value=True)
    def test_autonomous_zone_calls_reload(self, mock_reload):
        from modules.hot_reload import reload_zone
        result = reload_zone("autonomous")
        self.assertGreater(len(result), 0)
        self.assertTrue(all(v is True for v in result.values()))


class TestReloadAll(unittest.TestCase):
    """reload_all_autonomous, reload_all_supervised."""

    @unittest.mock.patch("modules.hot_reload.reload_module", return_value=True)
    def test_reload_all_autonomous(self, mock_reload):
        from modules.hot_reload import reload_all_autonomous
        result = reload_all_autonomous()
        self.assertGreater(len(result), 0)

    @unittest.mock.patch("modules.hot_reload.reload_module", return_value=True)
    def test_reload_all_supervised(self, mock_reload):
        from modules.hot_reload import reload_all_supervised
        result = reload_all_supervised()
        self.assertGreater(len(result), 0)


class TestReloadChangedFiles(unittest.TestCase):
    """reload_changed_files."""

    @unittest.mock.patch("modules.hot_reload.reload_module", return_value=True)
    def test_reload_one_file(self, mock_reload):
        from modules.hot_reload import reload_changed_files
        import modules.parser
        result = reload_changed_files(["modules/parser.py"])
        self.assertIn("modules.parser", result)

    @unittest.mock.patch("modules.hot_reload.reload_module", return_value=True)
    def test_reload_multiple_files(self, mock_reload):
        from modules.hot_reload import reload_changed_files
        import modules.parser
        import modules.tracer
        result = reload_changed_files(["modules/parser.py", "modules/tracer.py"])
        self.assertIn("modules.parser", result)
        self.assertIn("modules.tracer", result)

    @unittest.mock.patch("modules.hot_reload.reload_module")
    def test_nonexistent_file_skipped(self, mock_reload):
        from modules.hot_reload import reload_changed_files
        result = reload_changed_files(["nonexistent.py"])
        self.assertEqual(result, {})


class TestHotReloadSelfmod(unittest.TestCase):
    """hot_reload_selfmod."""

    @unittest.mock.patch("modules.hot_reload.reload_module", return_value=True)
    def test_autonomous_file_reloaded(self, mock_reload):
        from modules.hot_reload import hot_reload_selfmod
        import modules.parser
        result = hot_reload_selfmod(["modules/parser.py"])
        self.assertIn("modules.parser", result)
        self.assertTrue(result["modules.parser"])

    @unittest.mock.patch("modules.hot_reload.reload_module")
    def test_supervised_file_not_reloaded(self, mock_reload):
        from modules.hot_reload import hot_reload_selfmod
        import core.core
        result = hot_reload_selfmod(["core/core.py"])
        self.assertGreater(len(result), 0)
        self.assertFalse(list(result.values())[0])

    @unittest.mock.patch("modules.hot_reload.reload_module")
    def test_kernel_file_skipped(self, mock_reload):
        from modules.hot_reload import hot_reload_selfmod
        # kernel zone is empty, so no file maps to it
        result = hot_reload_selfmod(["unknown/file.txt"])
        self.assertEqual(result, {})


if __name__ == "__main__":
    unittest.main()