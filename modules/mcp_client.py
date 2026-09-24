# -*- coding: utf-8 -*-
# modules/mcp_client.py — MCP-клиент (HTTP/SSE)
#
# Подключается к MCP-серверу через SSE, получает список инструментов,
# регистрирует их в _GLOBAL_REGISTRY через @register_tool.
#
# v1: минимальная реализация — HTTP GET к SSE endpoint.

import json
import os
import re
import requests
import core
from core.core_tools import register_tool, _GLOBAL_REGISTRY


class MCPClient:
    """
    MCP-клиент: подключается к MCP-серверу и регистрирует его инструменты.

    v1 реализация:
    - HTTP-подключение к SSE endpoint
    - Получение списка инструментов через HTTP GET /tools
    - Регистрация в _GLOBAL_REGISTRY через register_tool

    Пример:
        client = MCPClient("http://localhost:3000")
        client.connect()
        client.register_tools()
        # инструменты теперь доступны агентам через list_dir, fetch_url, ...
    """

    def __init__(self, server_url: str = "http://localhost:3000",
                 tools_endpoint: str = "/tools"):
        self.server_url = server_url.rstrip("/")
        self.tools_endpoint = tools_endpoint
        self._tools_data = []
        self._connected = False

    def connect(self) -> bool:
        """Подключается к MCP-серверу и получает список инструментов."""
        try:
            url = f"{self.server_url}{self.tools_endpoint}"
            core.console.print(f"[yellow]🔌 MCP: подключение к {url}...[/yellow]")

            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            if isinstance(data, list):
                self._tools_data = data
            elif isinstance(data, dict) and "tools" in data:
                self._tools_data = data["tools"]
            else:
                core.console.print(f"[red]❌ MCP: неожиданный формат ответа[/red]")
                return False

            self._connected = True
            core.console.print(f"[green]✅ MCP: подключено, {len(self._tools_data)} инструментов[/green]")
            return True

        except requests.RequestException as e:
            core.console.print(f"[red]❌ MCP: ошибка подключения: {e}[/red]")
            return False

    def register_tools(self):
        """Регистрирует инструменты MCP-сервера в _GLOBAL_REGISTRY."""
        if not self._connected or not self._tools_data:
            core.console.print("[yellow]⚠️ MCP: нет подключения или инструментов[/yellow]")
            return

        for tool_info in self._tools_data:
            name = tool_info.get("name", "")
            description = tool_info.get("description", "")
            if not name:
                continue

            # Регистрируем функцию-враппер, которая вызывает MCP-сервер
            @register_tool(name, description)
            def _mcp_wrapper(args: str = "", _name=name, _server=self.server_url):
                """Выполняет инструмент на MCP-сервере."""
                try:
                    url = f"{_server}/call"
                    payload = {"tool": _name, "args": args}
                    resp = requests.post(url, json=payload, timeout=30)
                    resp.raise_for_status()
                    return resp.text
                except requests.RequestException as e:
                    return f"MCP error: {e}"

            core.console.print(f"  [dim]➕ {name}: {description[:60]}[/dim]")

        core.console.print(f"[green]✅ MCP: зарегистрировано {len(self._tools_data)} инструментов[/green]")