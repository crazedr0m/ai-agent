# -*- coding: utf-8 -*-
# mcp_servers/filesystem/server.py — FastMCP-инстанс filesystem-сервера
#
# Создаёт инстанс FastMCP и импортирует tools,
# чтобы декораторы @mcp.tool() зарегистрировали инструменты.
#
# Порядок важен: mcp создаётся ДО импорта tools.py,
# это гарантирует отсутствие циклических зависимостей.

from fastmcp import FastMCP

mcp = FastMCP(
    "filesystem-server",
    instructions="Filesystem operations: read, write, list, search, stat",
    version="1.0.0",
)

# Импорт tools для регистрации инструментов
import mcp_servers.filesystem.tools  # noqa: F401