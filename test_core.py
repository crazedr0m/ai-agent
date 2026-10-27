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


class TestMCPManager(unittest.TestCase):
    """Тесты для MCPManager (Фаза 3)."""

    def test_mcp_manager_no_config(self):
        """MCPManager.load_config() возвращает [] если нет конфига."""
        from modules.mcp_client import MCPManager

        manager = MCPManager(config_path="/nonexistent/path/mcp_servers.json")
        servers = manager.load_config()
        self.assertEqual(servers, [])

    def test_mcp_manager_connect_all_no_servers(self):
        """connect_all() возвращает 0 если нет серверов."""
        from modules.mcp_client import MCPManager

        manager = MCPManager(config_path="/nonexistent/path/mcp_servers.json")
        count = manager.connect_all()
        self.assertEqual(count, 0)

    def test_mcp_tool_registry_empty(self):
        """_MCP_TOOL_REGISTRY пуст до подключения."""
        from modules.mcp_client import _MCP_TOOL_REGISTRY
        self.assertEqual(len(_MCP_TOOL_REGISTRY), 0)

    def test_mcp_server_config_stdio(self):
        """MCPServerConfig корректно парсит stdio-конфиг."""
        from modules.mcp_client import MCPServerConfig

        config = MCPServerConfig("test", {
            "transport": "stdio",
            "command": "python",
            "args": ["-m", "test_server"],
            "description": "Test server",
        })
        self.assertEqual(config.name, "test")
        self.assertEqual(config.transport, "stdio")
        self.assertEqual(config.command, "python")
        self.assertEqual(config.args, ["-m", "test_server"])
        self.assertEqual(config.tool_prefix, "test__")

    def test_mcp_server_config_sse(self):
        """MCPServerConfig корректно парсит SSE-конфиг."""
        from modules.mcp_client import MCPServerConfig

        config = MCPServerConfig("web", {
            "transport": "sse",
            "url": "http://localhost:8080/sse",
        })
        self.assertEqual(config.transport, "sse")
        self.assertEqual(config.url, "http://localhost:8080/sse")

    def test_mcp_server_config_defaults(self):
        """MCPServerConfig использует значения по умолчанию."""
        from modules.mcp_client import MCPServerConfig

        config = MCPServerConfig("minimal", {
            "transport": "stdio",
            "command": "echo",
        })
        self.assertEqual(config.args, [])
        self.assertEqual(config.env, {})
        self.assertEqual(config.timeout, 30)
        self.assertEqual(config.description, "")


class TestMCPServerFilesystem(unittest.TestCase):
    """Контрактные тесты для Filesystem MCP-сервера (Фаза 3.4)."""

    def setUp(self):
        """Создаём временную директорию для тестов."""
        import tempfile
        import shutil
        self.tmpdir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.tmpdir)

        # Создаём тестовые файлы
        with open("test.txt", "w") as f:
            f.write("line1\nline2\nline3\n")
        os.makedirs("subdir", exist_ok=True)
        with open("subdir/nested.py", "w") as f:
            f.write("def hello():\n    pass\n")

    def tearDown(self):
        import shutil
        os.chdir(self.old_cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_list_dir(self):
        """list_dir показывает содержимое папки."""
        from mcp_servers.filesystem.tools import list_dir
        result = list_dir(".")
        self.assertIn("test.txt", result)
        self.assertIn("subdir/", result)

    def test_read_file(self):
        """read_file читает файл."""
        from mcp_servers.filesystem.tools import read_file
        result = read_file("test.txt")
        self.assertIn("line1", result)
        self.assertIn("line3", result)

    def test_read_file_range(self):
        """read_file с диапазоном строк."""
        from mcp_servers.filesystem.tools import read_file
        result = read_file("test.txt", start_line=2, end_line=2)
        self.assertIn("line2", result)
        self.assertNotIn("line1", result)

    def test_read_file_not_found(self):
        """read_file возвращает ошибку для несуществующего файла."""
        from mcp_servers.filesystem.tools import read_file
        result = read_file("nonexistent.txt")
        self.assertIn("не найден", result)

    def test_write_file(self):
        """write_file создаёт файл."""
        from mcp_servers.filesystem.tools import write_file
        result = write_file("new.txt", "hello world")
        self.assertIn("записан", result)
        self.assertTrue(os.path.exists("new.txt"))
        with open("new.txt") as f:
            self.assertEqual(f.read(), "hello world")

    def test_search_files(self):
        """search_files находит файлы по glob."""
        from mcp_servers.filesystem.tools import search_files
        result = search_files("*.txt")
        self.assertIn("test.txt", result)

    def test_stat_file(self):
        """stat_file показывает информацию о файле."""
        from mcp_servers.filesystem.tools import stat_file
        result = stat_file("test.txt")
        self.assertIn("Файл", result)
        self.assertIn("Размер", result)

    def test_grep_code(self):
        """grep_code находит строки по regex."""
        from mcp_servers.filesystem.tools import grep_code
        result = grep_code("line[12]", ".", file_pattern="*.txt")
        self.assertIn("test.txt", result)
        self.assertIn("line1", result)
        self.assertIn("line2", result)
        self.assertNotIn("line3", result)


class TestMCPServerFetch(unittest.TestCase):
    """Контрактные тесты для Web Fetch MCP-сервера (Фаза 3.4)."""

    def test_fetch_url_invalid(self):
        """fetch_url возвращает ошибку для невалидного URL."""
        from mcp_servers.fetch.tools import fetch_url
        result = fetch_url("http://localhost:1")
        self.assertTrue(
            "Error" in result or "ошибка" in result.lower() or "refused" in result.lower()
        )

    def test_fetch_markdown_invalid(self):
        """fetch_markdown возвращает ошибку для невалидного URL."""
        from mcp_servers.fetch.tools import fetch_markdown
        result = fetch_markdown("http://localhost:1")
        self.assertTrue(
            "Error" in result or "ошибка" in result.lower() or "refused" in result.lower()
        )


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


class TestExecuteToolCall(unittest.TestCase):
    """Тесты для ReActEngine.execute_tool_call (парсинг <call name=\"...\">)."""

    def setUp(self):
        # Регистрируем инструменты перед тестом
        import core_tools  # noqa
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


class TestPhase4Sandbox(unittest.TestCase):
    """Тесты для Sandbox (Фаза 4.2)."""

    def test_sandbox_not_git_repo(self):
        """Sandbox падает если не git-репозиторий."""
        import tempfile
        import os
        tmpdir = tempfile.mkdtemp()
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            from modules.sandbox import Sandbox, SandboxError
            with self.assertRaises(SandboxError):
                with Sandbox("test"):
                    pass
        finally:
            os.chdir(old_cwd)
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_sandbox_error_class(self):
        """SandboxError — исключение."""
        from modules.sandbox import SandboxError
        e = SandboxError("test error")
        self.assertIn("test error", str(e))


class TestPhase4Gate(unittest.TestCase):
    """Тесты для Gate (Фаза 4.3)."""

    def test_gate_check_tests_only(self):
        """check_tests_only запускает тесты (через echo)."""
        from modules.gate import Gate
        import sys
        gate = Gate(test_command=[sys.executable, "-c", "exit(0)"])
        result = gate.check_tests_only()
        self.assertTrue(result)

    def test_gate_kernel_denied(self):
        """kernel-зона всегда DENIED."""
        from modules.gate import Gate
        gate = Gate()
        result = gate.check("test", zone="kernel")
        self.assertFalse(result)

    def test_gate_autonomous_passes(self):
        """autonomous-зона проходит если тесты ок."""
        from modules.gate import Gate
        import sys
        gate = Gate(test_command=[sys.executable, "-c", "exit(0)"])
        result = gate.check("test", zone="autonomous")
        self.assertTrue(result)

    def test_gate_get_results(self):
        """get_results возвращает словарь."""
        from modules.gate import Gate
        import sys
        gate = Gate(test_command=[sys.executable, "-c", "exit(0)"])
        gate.check("test", zone="autonomous")
        results = gate.get_results()
        self.assertIn("verdict", results)
        self.assertIn("checks", results)


class TestPhase4Retrospective(unittest.TestCase):
    """Тесты для Retrospective (Фаза 4.4)."""

    def test_retrospective_empty(self):
        """Ретроспектива без трейсов не падает."""
        from modules.retrospective import Retrospective
        retro = Retrospective(traces_dir="/nonexistent/traces")
        report = retro.analyze()
        self.assertEqual(report.total_sessions, 0)
        self.assertEqual(report.total_errors, 0)

    def test_retro_report_summary(self):
        """RetroReport.summary возвращает строку."""
        from modules.retrospective import RetroReport
        report = RetroReport(total_sessions=1, total_errors=0, total_tool_calls=5)
        summary = report.summary
        self.assertIn("Ретроспектива", summary)
        self.assertIn("1", summary)

    def test_retro_report_save(self):
        """RetroReport.save() сохраняет JSON."""
        from modules.retrospective import RetroReport
        import tempfile, os, json
        report = RetroReport(total_sessions=1, total_errors=2, total_tool_calls=3)
        report.add_finding("test", "test finding", 2, "fix it")
        tmpfile = tempfile.mktemp(suffix=".json")
        try:
            report.save(tmpfile)
            self.assertTrue(os.path.exists(tmpfile))
            with open(tmpfile) as f:
                data = json.load(f)
            self.assertEqual(data["total_sessions"], 1)
            self.assertEqual(len(data["findings"]), 1)
        finally:
            if os.path.exists(tmpfile):
                os.unlink(tmpfile)


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
        """_mcp_server_files генерирует корректный код subpackage."""
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


class TestPhase4HotReload(unittest.TestCase):
    """Тесты для Hot Reload (Фаза 4.6)."""

    def test_filepath_to_module(self):
        """_filepath_to_module конвертирует пути."""
        from modules.hot_reload import _filepath_to_module
        # Проверяем только загруженные модули
        import core
        import modules.parser
        self.assertEqual(_filepath_to_module("modules/parser.py"), "modules.parser")
        self.assertEqual(_filepath_to_module("core/core.py"), "core.core")
        # Незагруженный модуль возвращает None
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