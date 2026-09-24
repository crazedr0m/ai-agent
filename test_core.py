# -*- coding: utf-8 -*-
# test_core.py — Расширенные тесты для v1 архитектуры
#
# Правила:
# - unittest (не pytest)
# - subprocess.run() для внешних тестов
# - returncode == 0 как критерий успеха

import unittest
import unittest.mock
import os
import sys
import json
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import core


class TestBaseAgent(unittest.TestCase):
    """Тесты для BaseAgent и ReActEngine."""

    def setUp(self):
        # Мокаем call_ollama внутри core.core (где живут ReActEngine/BaseAgent)
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
        # Регистрируем тестовый инструмент
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
            BaseAgent()  # noqa: abstract

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
        # Мок возвращает "Финальный ответ модели" (side_effect[0])
        self.assertEqual(result, "Финальный ответ модели")
        self._mock_ollama.assert_called_once_with("sys", "usr",
                                                  "qwen2.5-coder:14b")

    def test_agent_load_prompt(self):
        """load_prompt загружает из prompts.json."""
        # Создаём временный prompts.json
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


class TestTracer(unittest.TestCase):
    """Тесты для TraceSession и StepTrace."""

    def setUp(self):
        self.traces_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.traces_dir, ignore_errors=True)

    def test_step_trace_to_dict(self):
        """StepTrace сериализуется в dict."""
        from modules.tracer import StepTrace

        step = StepTrace("llm_call", "test content",
                         {"model": "qwen2.5-coder:14b"})
        data = step.to_dict()
        self.assertEqual(data["type"], "llm_call")
        self.assertEqual(data["content"], "test content")
        self.assertEqual(data["metadata"]["model"], "qwen2.5-coder:14b")
        self.assertIn("timestamp", data)

    def test_step_trace_from_dict(self):
        """StepTrace десериализуется из dict."""
        from modules.tracer import StepTrace

        data = {
            "type": "tool_call",
            "content": "list_dir .",
            "metadata": {"tool_name": "list_dir"},
            "timestamp": "2026-01-01T00:00:00Z"
        }
        step = StepTrace.from_dict(data)
        self.assertEqual(step.step_type, "tool_call")
        self.assertEqual(step.content, "list_dir .")
        self.assertEqual(step.metadata["tool_name"], "list_dir")

    def test_trace_session_writes_jsonl(self):
        """TraceSession пишет JSONL-файл."""
        from modules.tracer import TraceSession

        with TraceSession("test_agent",
                          traces_dir=self.traces_dir) as session:
            session.log_llm_call("system prompt", model="test-model")
            session.log_tool_call("list_dir", "/tmp", "file1\nfile2")
            session.log_final("Done")

        self.assertTrue(os.path.exists(session.jsonl_path))

        with open(session.jsonl_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        self.assertGreaterEqual(len(lines), 4)

        records = [json.loads(line.strip()) for line in lines if line.strip()]
        types = [r["type"] for r in records]
        self.assertIn("__session_start__", types)
        self.assertIn("llm_call", types)
        self.assertIn("tool_call", types)
        self.assertIn("tool_result", types)
        self.assertIn("final", types)
        self.assertIn("__session_end__", types)

    def test_trace_session_context_manager(self):
        """TraceSession работает как context manager."""
        from modules.tracer import TraceSession, StepTrace

        with TraceSession("test_ctx",
                          traces_dir=self.traces_dir) as session:
            self.assertFalse(session._closed)
            session.log_step(StepTrace("system", "test"))

        self.assertTrue(session._closed)

    def test_trace_session_rotation(self):
        """TraceSession удаляет старые сессии при превышении лимита."""
        from modules.tracer import TraceSession, StepTrace

        max_sessions = 3
        sessions = []
        for i in range(max_sessions + 2):
            session = TraceSession(f"test_{i}",
                                   traces_dir=self.traces_dir,
                                   max_sessions=max_sessions)
            session.close()
            sessions.append(session)

        remaining = [d for d in os.listdir(self.traces_dir)
                     if d.startswith("session_")]
        self.assertLessEqual(len(remaining), max_sessions)


class TestMCPClient(unittest.TestCase):
    """Тесты для MCPClient (mocked HTTP)."""

    def test_mcp_client_connect_fail(self):
        """MCPClient.connect() возвращает False при ошибке подключения."""
        from modules.mcp_client import MCPClient

        client = MCPClient("http://localhost:1")
        result = client.connect()
        self.assertFalse(result)

    def test_mcp_client_not_connected_register(self):
        """register_tools без connect не падает."""
        from modules.mcp_client import MCPClient

        client = MCPClient()
        try:
            client.register_tools()
        except Exception as e:
            self.fail(f"register_tools упал: {e}")


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
        result = core_tools.read_file_chunk("test_core.py", 9, 13)
        self.assertIn("import", result)

    def test_tools_registered_via_decorator(self):
        """Инструменты зарегистрированы через @register_tool."""
        from core.core_tools import _GLOBAL_REGISTRY
        import core_tools  # noqa: регистрирует инструменты

        for name in ["list_dir", "view_file_outline",
                     "read_file_chunk", "query_db_schema"]:
            self.assertIn(name, _GLOBAL_REGISTRY,
                          f"{name} не зарегистрирован")


class TestExecuteModelTools(unittest.TestCase):
    """Тесты для execute_model_tools (парсинг <call name=\"...\">)."""

    def setUp(self):
        # Регистрируем инструменты перед тестом
        import core_tools  # noqa

    def test_parse_tool_call(self):
        """Парсинг простого вызова инструмента."""
        found, result = core.execute_model_tools(
            '<call name="list_dir">.</call>')
        self.assertTrue(found)
        self.assertIn("<tool_result", result)

    def test_parse_no_tool_call(self):
        """Нет вызова — возвращает (False, '')."""
        found, result = core.execute_model_tools(
            "Просто текст без инструментов")
        self.assertFalse(found)
        self.assertEqual(result, "")

    def test_parse_unknown_tool(self):
        """Неизвестный инструмент — возвращает ошибку."""
        found, result = core.execute_model_tools(
            '<call name="nonexistent">arg</call>')
        self.assertTrue(found)
        self.assertIn("не зарегистрирован", result)


if __name__ == "__main__":
    unittest.main()