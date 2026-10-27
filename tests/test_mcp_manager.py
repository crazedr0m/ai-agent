# -*- coding: utf-8 -*-
# tests/test_mcp_manager.py — Тесты для MCPManager (Фаза 3)

import unittest

from tests import *  # noqa: sys.path


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


if __name__ == "__main__":
    unittest.main()