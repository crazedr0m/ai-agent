# -*- coding: utf-8 -*-
# tests/test_zones.py — Тесты зон мутабельности (ADR-001) и их исполнения в dev_tools

import unittest
from unittest.mock import patch, mock_open

from modules.zones import (
    describe_zone,
    is_writable_without_approval,
    relative_to_project,
    zone_of,
)
from modules.settings import PROJECT_ROOT


class TestZoneOf(unittest.TestCase):
    """zone_of()."""

    def test_supervised_core_dir(self):
        self.assertEqual(zone_of("core/runtime.py"), "supervised")
        self.assertEqual(zone_of("core/core.py"), "supervised")
        self.assertEqual(zone_of("core/core_tools.py"), "supervised")
        self.assertEqual(zone_of("core/__init__.py"), "supervised")

    def test_autonomous_agents(self):
        self.assertEqual(zone_of("agents/casual_agent.py"), "autonomous")

    def test_autonomous_modules(self):
        self.assertEqual(zone_of("modules/tool_parser.py"), "autonomous")

    def test_autonomous_prompts(self):
        self.assertEqual(zone_of("prompts.json"), "autonomous")
        self.assertEqual(zone_of("prompts/coder_developer.txt"), "autonomous")

    def test_autonomous_root_core_tools(self):
        self.assertEqual(zone_of("core_tools.py"), "autonomous")

    def test_autonomous_mcp_servers(self):
        self.assertEqual(zone_of("mcp_servers/fetch/tools.py"), "autonomous")

    def test_kernel_venv(self):
        self.assertEqual(zone_of("venv/lib/python3.11/site-packages/x.py"), "kernel")

    def test_kernel_git(self):
        self.assertEqual(zone_of(".git/config"), "kernel")

    def test_unknown_returns_none(self):
        self.assertIsNone(zone_of("unknown/file.txt"))
        self.assertIsNone(zone_of("docs/readme.md"))

    def test_absolute_path_inside_project(self):
        abs_path = str(PROJECT_ROOT / "modules" / "parser.py")
        self.assertEqual(zone_of(abs_path), "autonomous")

    def test_absolute_path_kernel(self):
        abs_path = str(PROJECT_ROOT / "venv" / "bin" / "python")
        self.assertEqual(zone_of(abs_path), "kernel")

    def test_absolute_path_outside_project_returns_none(self):
        self.assertIsNone(zone_of("/etc/passwd"))

    def test_empty_path_returns_none(self):
        self.assertIsNone(zone_of(""))

    def test_backslash_normalized(self):
        self.assertEqual(zone_of("modules\\tui\\app.py"), "autonomous")


class TestRelativeToProject(unittest.TestCase):
    """relative_to_project()."""

    def test_relative_kept(self):
        self.assertEqual(relative_to_project("modules/x.py"), "modules/x.py")

    def test_strip_dot_slash(self):
        self.assertEqual(relative_to_project("./modules/x.py"), "modules/x.py")

    def test_absolute_inside(self):
        abs_path = str(PROJECT_ROOT / "agents" / "a.py")
        self.assertEqual(relative_to_project(abs_path), "agents/a.py")

    def test_absolute_outside(self):
        self.assertIsNone(relative_to_project("/etc/passwd"))

    def test_empty(self):
        self.assertIsNone(relative_to_project(""))


class TestHelpers(unittest.TestCase):
    """is_writable_without_approval / describe_zone."""

    def test_only_autonomous_is_free(self):
        self.assertTrue(is_writable_without_approval("modules/x.py"))
        self.assertFalse(is_writable_without_approval("core/runtime.py"))
        self.assertFalse(is_writable_without_approval("venv/x.py"))
        self.assertFalse(is_writable_without_approval("unknown/x.py"))

    def test_describe(self):
        self.assertIn("kernel", describe_zone("kernel"))
        self.assertIn("подтверждение", describe_zone("supervised"))
        self.assertIn("самостоятельно", describe_zone("autonomous"))
        self.assertIn("вне", describe_zone(None))


class TestDevToolsZoneEnforcement(unittest.TestCase):
    """write_file/apply_diff соблюдают зоны ADR-001."""

    def test_write_kernel_blocked_without_confirm(self):
        with patch("modules.dev_tools.confirm_action") as mock_confirm:
            from modules.dev_tools import write_file
            result = write_file("venv/evil.py", "payload")
        self.assertIn("kernel", result)
        self.assertIn("❌", result)
        mock_confirm.assert_not_called()

    def test_write_supervised_requires_confirmation(self):
        with patch("modules.dev_tools.confirm_action", return_value=False) as mock_confirm:
            from modules.dev_tools import write_file
            result = write_file("core/runtime.py", "new content")
        self.assertIn("❌", result)
        mock_confirm.assert_called_once()

    def test_write_supervised_approved(self):
        with patch("modules.dev_tools.confirm_action", return_value=True):
            with patch("builtins.open", mock_open()):
                with patch("os.makedirs"):
                    from modules.dev_tools import write_file
                    result = write_file("core/runtime.py", "new content")
        self.assertIn("✅", result)

    def test_write_autonomous_no_confirm_needed(self):
        with patch("modules.dev_tools.confirm_action") as mock_confirm:
            with patch("builtins.open", mock_open()):
                with patch("os.makedirs"):
                    from modules.dev_tools import write_file
                    result = write_file("modules/parser.py", "content")
        self.assertIn("✅", result)
        mock_confirm.assert_not_called()

    def test_apply_diff_kernel_blocked(self):
        with patch("modules.dev_tools.confirm_action") as mock_confirm:
            from modules.dev_tools import apply_diff
            result = apply_diff(".git/config", "a", "b")
        self.assertIn("kernel", result)
        mock_confirm.assert_not_called()

    def test_apply_diff_supervised_denied(self):
        with patch("modules.dev_tools.confirm_action", return_value=False):
            from modules.dev_tools import apply_diff
            result = apply_diff("core/core.py", "old", "new")
        self.assertIn("❌", result)


if __name__ == "__main__":
    unittest.main()