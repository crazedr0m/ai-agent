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

    def test_run_react_returns_engine_result(self):
        """run_react делегирует в engine.execute и возвращает строку.

        Регрессия: тело метода было утеряно, run_react возвращал None,
        что давало 'NoneType' object is not subscriptable в агентах.
        """
        from core.core import BaseAgent

        class TestAgent(BaseAgent):
            def run(self):
                return self.run_react("sys", "usr")

        agent = TestAgent(max_steps=3)
        result = agent.run()
        self.assertIsNotNone(result)
        self.assertEqual(result, "Финальный ответ модели")

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


class TestReActTracing(unittest.TestCase):
    """Регрессия: ReActEngine пишет tool_call/tool_result в trace.jsonl."""

    def setUp(self):
        self._patcher = unittest.mock.patch('core.core._root_core.call_ollama')
        self._mock_ollama = self._patcher.start()
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        self._patcher.stop()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _read_trace(self, session):
        with open(session.jsonl_path, "r", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    def test_tool_call_and_result_logged(self):
        """Успешный вызов инструмента попадает в трейс с аргументами."""
        from core.core_tools import register_tool
        from core.core import ReActEngine
        from modules.tracer import TraceSession

        @register_tool("trace_tool", "Test")
        def trace_tool(arg: str) -> str:
            return f"ok:{arg}"

        self._mock_ollama.side_effect = [
            '<call name="trace_tool">hello</call>',
            "Готово",
        ]

        session = TraceSession("test_agent", traces_dir=self.tmpdir)
        engine = ReActEngine(max_steps=5, tracer=session)
        engine.execute("system", "user")
        session.close()

        records = self._read_trace(session)
        types = [r["type"] for r in records]
        self.assertIn("llm_call", types)
        self.assertIn("tool_call", types)
        self.assertIn("tool_result", types)

        call = next(r for r in records if r["type"] == "tool_call")
        self.assertEqual(call["metadata"]["tool_name"], "trace_tool")
        self.assertIn("hello", call["metadata"]["args"])

        result = next(r for r in records if r["type"] == "tool_result")
        self.assertIn("ok:hello", result["content"])
        self.assertFalse(result["metadata"].get("error", False))

    def test_invalid_args_trigger_repair(self):
        """Невалидные аргументы → ошибка возвращается модели (repair), не pass."""
        from core.core_tools import register_tool
        from core.core import ReActEngine

        @register_tool("strict_tool", "Test")
        def strict_tool(required_arg: str) -> str:
            return "never"

        engine = ReActEngine(max_steps=3)
        found, result = engine.execute_tool_call(
            '<call name="strict_tool">{"wrong": "x"}</call>')
        self.assertTrue(found)
        self.assertNotIn("<tool_result", result)
        self.assertIn("Ошибка вызова", result)


if __name__ == "__main__":
    unittest.main()