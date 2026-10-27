# -*- coding: utf-8 -*-
# tests/test_base_agent.py — Тесты для BaseAgent и ReActEngine
#
# Классы:
#   TestBaseAgent       — базовые тесты BaseAgent + ReActEngine
#   TestExecuteToolCall — тесты парсинга <call name="...">

import unittest
import unittest.mock
import os
import sys
import json
import tempfile
import shutil

from tests import *  # noqa: sys.path


class TestBaseAgent(unittest.TestCase):
    """Тесты для BaseAgent и ReActEngine."""

    def setUp(self):
        self._patcher = unittest.mock.patch('core.core._root_core.call_ollama')
        self._mock_ollama = self._patcher.start()
        self._mock_ollama.side_effect = [
            "Финальный ответ модели"
        ]

    def tearDown(self):
        self._patcher.stop()

    def test_react_engine_basic(self):
        """ReActEngine возвращает финальный ответ."""
        from core.core import ReActEngine

        engine = ReActEngine(max_steps=3)
        result = engine.execute("system prompt", "user prompt")
        self.assertEqual(result, "Финальный ответ модели")

    def test_react_engine_with_tool_call(self):
        """ReActEngine обрабатывает вызов инструмента и возвращает ответ."""
        from core.core_tools import register_tool

        @register_tool("test_tool2", "Test")
        def test_tool(arg: str) -> str:
            return f"result: {arg}"

        self._mock_ollama.side_effect = [
            '<call name="test_tool2">hello</call>',
            "Финальный ответ",
        ]

        engine = __import__("core.core", fromlist=["ReActEngine"]).ReActEngine(max_steps=5)
        result = engine.execute("system", "user")
        self.assertEqual(result, "Финальный ответ")
        self.assertEqual(self._mock_ollama.call_count, 2)

    def test_base_agent_cannot_instantiate(self):
        """BaseAgent абстрактный — нельзя инстанцировать напрямую."""
        from core.core import BaseAgent

        with self.assertRaises(TypeError):
            BaseAgent()

    def test_base_agent_subclass(self):
        """Наследник BaseAgent работает."""
        from core.core import BaseAgent

        class TestAgent(BaseAgent):
            def run(self):
                return "ok"

        agent = TestAgent(name="test_agent", max_steps=3)
        self.assertEqual(agent.name, "test_agent")
        self.assertEqual(agent.run(), "ok")

    def test_agent_call_llm(self):
        """call_llm делегирует в core._root_core.call_ollama."""
        from core.core import BaseAgent

        class TestAgent(BaseAgent):
            def run(self):
                return self.call_llm("sys", "usr")

        agent = TestAgent()
        result = agent.run()
        self.assertEqual(result, "Финальный ответ модели")
        self._mock_ollama.assert_called_once_with("sys", "usr",
                                                  "qwen2.5-coder:14b")

    def test_agent_load_prompt(self):
        """load_prompt загружает из prompts.json."""
        tmpdir = tempfile.mkdtemp()
        old_cwd = os.getcwd()
        os.chdir(tmpdir)

        try:
            os.makedirs("prompts", exist_ok=True)
            with open("prompts/test_role.txt", "w", encoding="utf-8") as f:
                f.write("test prompt content")

            config = {
                "test_role": {
                    "file_path": "prompts/test_role.txt",
                    "description": "Test",
                    "mutability": "autonomous"
                }
            }
            with open("prompts.json", "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            from core.core import BaseAgent

            class TestAgent(BaseAgent):
                def run(self):
                    return self.load_prompt("test_role")

            agent = TestAgent()
            result = agent.run()
            self.assertEqual(result.strip(), "test prompt content")
        finally:
            os.chdir(old_cwd)
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestExecuteToolCall(unittest.TestCase):
    """Тесты для ReActEngine.execute_tool_call (парсинг <call name="...">)."""

    def setUp(self):
        import core_tools  # noqa: регистрирует инструменты
        from core.core import ReActEngine
        self.engine = ReActEngine(max_steps=3)

    def test_parse_tool_call(self):
        """Парсинг простого вызова инструмента."""
        found, result = self.engine.execute_tool_call(
            '<call name="list_dir">.</call>')
        self.assertTrue(found)
        self.assertIn("<tool_result", result)

    def test_parse_no_tool_call(self):
        """Нет вызова — возвращает (False, '')."""
        found, result = self.engine.execute_tool_call(
            "Просто текст без инструментов")
        self.assertFalse(found)
        self.assertEqual(result, "")

    def test_parse_unknown_tool(self):
        """Неизвестный инструмент — возвращает ошибку."""
        found, result = self.engine.execute_tool_call(
            '<call name="nonexistent">arg</call>')
        self.assertTrue(found)
        self.assertIn("не зарегистрирован", result)


if __name__ == "__main__":
    unittest.main()