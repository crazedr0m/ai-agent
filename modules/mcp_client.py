# -*- coding: utf-8 -*-
# modules/mcp_client.py — MCP-клиент на базе официального mcp SDK
#
# Фаза 3: замена самодельного HTTP-клиента на официальный mcp SDK.
# Поддерживает stdio, SSE, streamable_http транспорты.
#
# Использование:
#     from modules.mcp_client import MCPManager
#     manager = MCPManager()
#     count = manager.connect_all()  # подключается ко всем серверам из mcp_servers.json
#     # инструменты автоматически зарегистрированы в ToolRegistry

import asyncio
import json
import logging
import os
import sys
from typing import Any, Optional

from mcp import Client
from core.core_tools import register_tool, _GLOBAL_REGISTRY

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Глобальный event loop для bridging async → sync
# ═══════════════════════════════════════════════════════════════════

_LOOP: Optional[asyncio.AbstractEventLoop] = None


def _get_loop() -> asyncio.AbstractEventLoop:
    """Получить или создать глобальный event loop."""
    global _LOOP
    if _LOOP is None or _LOOP.is_closed():
        _LOOP = asyncio.new_event_loop()
    return _LOOP


def _run_async(coro):
    """Запустить асинхронную корутину в глобальном event loop."""
    return _get_loop().run_until_complete(coro)


# ═══════════════════════════════════════════════════════════════════
# Глобальный реестр MCP-инструментов (full_name -> (config, mcp_tool_name))
# ═══════════════════════════════════════════════════════════════════

_MCP_TOOL_REGISTRY: dict[str, tuple[Any, str]] = {}


# ═══════════════════════════════════════════════════════════════════
# MCPServerConfig
# ═══════════════════════════════════════════════════════════════════


def _resolve_command(command: Optional[str]) -> Optional[str]:
    """Подставляет интерпретатор текущего venv вместо голого 'python'."""
    if command not in ("python", "python3"):
        return command
    candidate = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "venv", "bin", "python")
    if os.path.exists(candidate):
        return candidate
    return sys.executable or command


class MCPServerConfig:
    """Конфигурация одного MCP-сервера."""

    def __init__(self, name: str, config: dict):
        self.name = name
        self.transport = config.get("transport", "stdio")
        self.command = config.get("command")
        self.args = config.get("args", [])
        self._env = config.get("env", {})
        self.url = config.get("url")
        self.timeout = config.get("timeout", 30)
        self.description = config.get("description", "")

    @property
    def env(self):
        """Окружение для дочернего процесса — родительский env + переопределения."""
        merged = dict(os.environ)
        merged.update(self._env)
        return merged

    @property
    def tool_prefix(self) -> str:
        """Префикс для инструментов этого сервера (например filesystem__)."""
        return f"{self.name}__"


# ═══════════════════════════════════════════════════════════════════
# Вспомогательные функции для вызова MCP-инструментов
# ═══════════════════════════════════════════════════════════════════


def _format_mcp_result(result) -> str:
    """Извлечь текст из CallToolResult."""
    texts = []
    for content in result.content:
        if hasattr(content, 'text') and content.text:
            texts.append(content.text)
        elif hasattr(content, 'data'):
            texts.append(str(content.data))
    if texts:
        return "\n".join(texts)
    return str(result)


class MCPToolError(RuntimeError):
    """Ошибка вызова MCP-инструмента (отличима от успешного результата)."""


async def _call_mcp_tool_async(
    server: MCPServerConfig,
    tool_name: str,
    arguments: dict,
) -> str:
    """Асинхронный вызов MCP-инструмента.

    При сбое поднимает MCPToolError, чтобы ReAct-цикл мог запустить repair,
    а не принимать ошибку за успешный результат.
    """
    from mcp import Client

    try:
        if server.transport == "stdio":
            from mcp.client.stdio import StdioServerParameters
            params = StdioServerParameters(
                command=server.command,
                args=server.args,
                env=server.env if server.env else None,
            )
            async with Client(params) as client:
                result = await client.call_tool(tool_name, arguments)
                return _format_mcp_result(result)

        elif server.transport == "sse":
            from mcp.client.sse import sse_client
            if not server.url:
                raise MCPToolError(
                    f"SSE transport requires 'url' for '{server.name}'")
            transport = sse_client(server.url)
            async with Client(transport) as client:
                result = await client.call_tool(tool_name, arguments)
                return _format_mcp_result(result)

        elif server.transport == "streamable_http":
            from mcp.client.streamable_http import streamable_http_client
            if not server.url:
                raise MCPToolError(
                    f"streamable_http transport requires 'url' for '{server.name}'")
            transport = streamable_http_client(server.url)
            async with Client(transport) as client:
                result = await client.call_tool(tool_name, arguments)
                return _format_mcp_result(result)

        else:
            raise MCPToolError(f"unknown transport '{server.transport}'")

    except MCPToolError:
        raise
    except Exception as e:
        logger.exception(f"MCP call failed: {server.name}/{tool_name}")
        raise MCPToolError(f"{server.name}/{tool_name}: {e}") from e


def _call_mcp_tool_sync(server: MCPServerConfig, tool_name: str, arguments: dict) -> str:
    """Синхронный вызов MCP-инструмента (обёртка над async)."""
    return _run_async(_call_mcp_tool_async(server, tool_name, arguments))


# ═══════════════════════════════════════════════════════════════════
# Регистрация инструмента-враппера
# ═══════════════════════════════════════════════════════════════════


def _register_mcp_tool(
    full_name: str,
    server: MCPServerConfig,
    mcp_tool_name: str,
    description: str,
    parameters: Optional[dict] = None,
):
    """Создать и зарегистрировать синхронную обёртку для MCP-инструмента.

    parameters: JSON Schema инструмента из MCP-сервера (inputSchema).
    Если не передана — схема генерируется из type hints обёртки.
    """
    _MCP_TOOL_REGISTRY[full_name] = (server, mcp_tool_name)

    @register_tool(full_name, description, parameters=parameters)
    def _wrapper(**kwargs: Any) -> str:
        """MCP tool wrapper — calls the remote server."""
        cfg, name = _MCP_TOOL_REGISTRY[full_name]
        return _call_mcp_tool_sync(cfg, name, kwargs)

    return _wrapper


# ═══════════════════════════════════════════════════════════════════
# MCPManager
# ═══════════════════════════════════════════════════════════════════


class MCPManager:
    """
    Менеджер MCP-подключений.

    Загружает конфиг из mcp_servers.json, подключается к серверам,
    регистрирует их инструменты в ToolRegistry с префиксом сервера.

    Пример:
        manager = MCPManager()
        count = manager.connect_all()
        print(f"{count} MCP tools registered")
    """

    def __init__(self, config_path: str = "mcp_servers.json"):
        self.config_path = config_path
        self.servers: dict[str, MCPServerConfig] = {}

    def load_config(self) -> list[MCPServerConfig]:
        """Загрузить конфиг из JSON-файла."""
        if not os.path.exists(self.config_path):
            logger.warning(f"MCP config not found: {self.config_path}")
            return []

        with open(self.config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        servers = []
        for name, cfg in data.get("servers", {}).items():
            server = MCPServerConfig(name, cfg)
            self.servers[name] = server
            servers.append(server)

        return servers

    def connect_all(self) -> int:
        """
        Подключиться ко всем серверам и зарегистрировать инструменты.

        Returns:
            int: количество зарегистрированных инструментов
        """
        servers = self.load_config()
        if not servers:
            return 0

        return _run_async(self._connect_all(servers))

    async def _connect_all(self, servers: list[MCPServerConfig]) -> int:
        """Подключиться ко всем серверам параллельно."""
        results = await asyncio.gather(
            *(self._connect_server(s) for s in servers),
            return_exceptions=True,
        )

        total = 0
        for server, result in zip(servers, results):
            if isinstance(result, BaseException):
                logger.error("MCP server '%s' failed: %s", server.name, result)
                continue
            total += result
            logger.info(
                "MCP server '%s': %d tools registered via %s",
                server.name, result, server.transport,
            )
        return total

    async def _connect_server(self, server: MCPServerConfig) -> int:
        """Подключиться к одному серверу и зарегистрировать его инструменты."""
        from mcp import Client

        if server.transport == "stdio":
            from mcp.client.stdio import StdioServerParameters
            params = StdioServerParameters(
                command=_resolve_command(server.command),
                args=server.args,
                env=server.env if server.env else None,
            )
            async with Client(params) as client:
                return await self._register_tools(client, server)

        elif server.transport == "sse":
            from mcp.client.sse import sse_client
            if not server.url:
                raise ValueError(f"SSE transport requires 'url' for '{server.name}'")
            transport = sse_client(server.url)
            async with Client(transport) as client:
                return await self._register_tools(client, server)

        elif server.transport == "streamable_http":
            from mcp.client.streamable_http import streamable_http_client
            if not server.url:
                raise ValueError(
                    f"streamable_http transport requires 'url' for '{server.name}'"
                )
            transport = streamable_http_client(server.url)
            async with Client(transport) as client:
                return await self._register_tools(client, server)

        else:
            raise ValueError(f"Unknown transport '{server.transport}' for '{server.name}'")

    async def _register_tools(self, client: Client, server: MCPServerConfig) -> int:
        """Получить инструменты с сервера и зарегистрировать их в ToolRegistry."""
        result = await client.list_tools()
        prefix = server.tool_prefix
        count = 0

        for tool in result.tools:
            mcp_tool_name = tool.name
            full_name = f"{prefix}{mcp_tool_name}"
            description = tool.description or f"MCP tool from {server.name}"

            schema = (getattr(tool, "input_schema", None)
                      or getattr(tool, "inputSchema", None))

            _register_mcp_tool(
                full_name=full_name,
                server=server,
                mcp_tool_name=mcp_tool_name,
                description=f"[MCP:{server.name}] {description}",
                parameters=schema,
            )
            count += 1

        return count


# ═══════════════════════════════════════════════════════════════════
# Удобная функция для подключения из agent.py
# ═══════════════════════════════════════════════════════════════════


def connect_mcp_servers(config_path: str = "mcp_servers.json") -> int:
    """
    Подключиться ко всем MCP-серверам из конфига.

    Returns:
        int: количество зарегистрированных инструментов
    """
    manager = MCPManager(config_path=config_path)
    return manager.connect_all()