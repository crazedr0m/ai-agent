# -*- coding: utf-8 -*-
# mcp_servers/fetch/server.py — FastMCP-инстанс fetch-сервера
#
# Создаёт инстанс FastMCP и импортирует tools,
# чтобы декораторы @mcp.tool() зарегистрировали инструменты.
#
# Порядок важен: mcp создаётся ДО импорта tools.py,
# это гарантирует отсутствие циклических зависимостей.

from fastmcp import FastMCP

mcp = FastMCP(
    "fetch-server",
    instructions="Web fetch: download URLs, convert HTML to markdown",
    version="1.0.0",
)

# Импорт tools для регистрации инструментов
import mcp_servers.fetch.tools  # noqa: F401