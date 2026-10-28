# -*- coding: utf-8 -*-
# tests/test_core_foundation.py — Тесты для _core.py (фундаментальные функции ядра)

import unittest
from unittest.mock import patch, MagicMock, mock_open
import json
import sys
import tempfile
import shutil

from tests import *  # noqa: sys.path


class TestLoadPrompt(unittest.TestCase):
    """Тесты для _core.load_prompt()."""

    @patch("builtins.open", new_callable=mock_open)
    def test_load_inline_prompt(self, mock_file):
        mock_file.return_value.read.side_effect = [
            json.dumps({"test_key": {"prompt": "hello world"}})
        ]
        import _core
        result = _core.load_prompt("test_key")
        self.assertEqual(result, "hello world")

    @patch("builtins.open", new_callable=mock_open)
    def test_load_file_path_prompt(self, mock_file):
        mock_file.return_value.read.side_effect = [
            json.dumps({"test_key": {"file_path": "prompts/test.txt"}}),
            "content from file",
        ]
        import _core
        result = _core.load_prompt("test_key")
        self.assertEqual(result, "content from file")

    @patch("builtins.open", new_callable=mock_open)
    def test_load_file_path_calls_read_twice(self, mock_file):
        mock_file.return_value.read.side_effect = [
            json.dumps({"k": {"file_path": "prompts/test.txt"}}),
            "file content",
        ]
        import _core
        _core.load_prompt("k")
        self.assertEqual(mock_file.call_count, 2)


class TestLoadPromptFromFile(unittest.TestCase):
    """Тесты для _core.load_prompt_from_file()."""

    @patch("builtins.open", new_callable=mock_open)
    def test_load_from_file_path(self, mock_file):
        mock_file.return_value.read.side_effect = [
            json.dumps({"k": {"file_path": "prompts/myprompt.txt"}}),
            "from file",
        ]
        import _core
        result = _core.load_prompt_from_file("k")
        self.assertEqual(result, "from file")

    @patch("builtins.open", new_callable=mock_open)
    def test_load_inline_prompt(self, mock_file):
        mock_file.return_value.read.side_effect = [
            json.dumps({"k": {"prompt": "inline text"}})
        ]
        import _core
        result = _core.load_prompt_from_file("k")
        self.assertEqual(result, "inline text")


class TestUpdatePromptFile(unittest.TestCase):
    """Тесты для _core.update_prompt_file()."""

    @patch("builtins.open", new_callable=mock_open)
    def test_update_immutable_blocked(self, mock_file):
        mock_file.return_value.read.side_effect = [
            json.dumps({"k": {"prompt": "old", "mutability": "immutable"}})
        ]
        with patch("_core.console") as mock_console:
            import _core
            result = _core.update_prompt_file("k", "new text")
        self.assertFalse(result)
        mock_console.print.assert_called_once()

    @patch("builtins.open", new_callable=mock_open)
    def test_update_file_path(self, mock_file):
        mock_file.return_value.read.side_effect = [
            json.dumps({"k": {"file_path": "prompts/test.txt", "mutability": "user_approved"}})
        ]
        with patch("_core.console"):
            import _core
            result = _core.update_prompt_file("k", "new content")

        self.assertTrue(result)
        write_calls = [c for c in mock_file.call_args_list if c[0][1] == 'w']
        self.assertEqual(len(write_calls), 1)
        self.assertEqual(write_calls[0][0][0], "prompts/test.txt")

    @patch("builtins.open", new_callable=mock_open)
    def test_update_inline_prompt(self, mock_file):
        mock_file.return_value.read.side_effect = [
            json.dumps({"k": {"prompt": "old", "mutability": "user_approved"}})
        ]
        with patch("_core.console"):
            import _core
            result = _core.update_prompt_file("k", "new inline text")

        self.assertTrue(result)
        write_call = [c for c in mock_file.call_args_list if c[0][1] == 'w'][-1]
        self.assertEqual(write_call[0][0], "prompts.json")


class TestUpdatePromptInFile(unittest.TestCase):
    """Тесты для _core.update_prompt_in_file()."""

    @patch("builtins.open", new_callable=mock_open)
    def test_update_immutable_blocked(self, mock_file):
        mock_file.return_value.read.side_effect = [
            json.dumps({"k": {"prompt": "old", "mutability": "immutable"}})
        ]
        with patch("_core.console"):
            import _core
            result = _core.update_prompt_in_file("k", "new")
        self.assertFalse(result)

    @patch("builtins.open", new_callable=mock_open)
    def test_update_with_file_path(self, mock_file):
        mock_file.return_value.read.side_effect = [
            json.dumps({"k": {"file_path": "prompts/test.txt", "mutability": "autonomous"}})
        ]
        with patch("_core.console"):
            import _core
            result = _core.update_prompt_in_file("k", "new content")
        self.assertTrue(result)

    @patch("builtins.open", new_callable=mock_open)
    def test_update_without_file_path_uses_default(self, mock_file):
        mock_file.return_value.read.side_effect = [
            json.dumps({"k": {"prompt": "old", "mutability": "autonomous"}})
        ]
        with patch("_core.console"):
            import _core
            result = _core.update_prompt_in_file("k", "new content")
        self.assertTrue(result)
        write_call = [c for c in mock_file.call_args_list if c[0][1] == 'w'][0]
        self.assertEqual(write_call[0][0], "prompts/k.txt")


class TestCallOllama(unittest.TestCase):
    """Тесты для _core.call_ollama()."""

    @patch("modules.llm.call_chat", return_value="model response")
    def test_call_ollama_delegates_to_call_chat(self, mock_call_chat):
        import _core
        result = _core.call_ollama("sys", "user")
        self.assertEqual(result, "model response")
        mock_call_chat.assert_called_once_with(
            system_prompt="sys",
            user_prompt="user",
            model_override=None,
        )

    @patch("modules.llm.call_chat", return_value="custom model response")
    def test_call_ollama_with_model_override(self, mock_call_chat):
        import _core
        result = _core.call_ollama("sys", "user", model_override="deepseek-r1:32b")
        self.assertEqual(result, "custom model response")
        mock_call_chat.assert_called_once_with(
            system_prompt="sys",
            user_prompt="user",
            model_override="deepseek-r1:32b",
        )


class TestRunIsolatedTests(unittest.TestCase):
    """Тесты для _core.run_isolated_tests()."""

    @patch("subprocess.run")
    def test_tests_pass(self, mock_subprocess):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        with patch("_core.console"):
            import _core
            success, message = _core.run_isolated_tests("test_abc.py")

        self.assertTrue(success)
        self.assertEqual(message, "Успех")

    @patch("subprocess.run")
    def test_tests_fail_uses_stderr(self, mock_subprocess):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "FAIL: test failed"
        mock_result.stdout = "some output"
        mock_subprocess.return_value = mock_result

        with patch("_core.console"):
            import _core
            success, message = _core.run_isolated_tests("test_abc.py")

        self.assertFalse(success)
        self.assertIn("FAIL: test failed", message)

    @patch("subprocess.run")
    def test_tests_fall_uses_stdout_if_no_stderr(self, mock_subprocess):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = ""
        mock_result.stdout = "some output"
        mock_subprocess.return_value = mock_result

        with patch("_core.console"):
            import _core
            success, message = _core.run_isolated_tests("test_abc.py")

        self.assertFalse(success)
        self.assertIn("some output", message)

    @patch("subprocess.run")
    def test_uses_sys_executable(self, mock_subprocess):
        with patch("_core.console"):
            import _core
            _core.run_isolated_tests("test_xyz.py")
        args, kwargs = mock_subprocess.call_args
        self.assertIn(sys.executable, args[0])


class TestHotReload(unittest.TestCase):
    """Тесты для _core.hot_reload()."""

    @patch("modules.hot_reload.reload_all_autonomous")
    def test_hot_reload_all_success(self, mock_reload_autonomous):
        mock_reload_autonomous.return_value = {
            "modules.parser": True,
            "modules.permissions": True,
        }

        with patch("_core.console"):
            import _core
            _core.hot_reload()

        mock_reload_autonomous.assert_called_once()

    @patch("modules.hot_reload.reload_all_autonomous")
    def test_hot_reload_some_failed(self, mock_reload_autonomous):
        mock_reload_autonomous.return_value = {
            "modules.ok": True,
            "modules.fail": False,
        }

        mock_console = MagicMock()
        with patch("_core.console", mock_console):
            import _core
            _core.hot_reload()

        print_calls = mock_console.print.call_args_list
        has_failed_message = any(
            "Не удалось" in str(c) for c in print_calls
        )
        self.assertTrue(
            has_failed_message,
            f"Expected 'Не удалось' in print calls, got: {print_calls}"
        )


if __name__ == "__main__":
    unittest.main()