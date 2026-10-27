# -*- coding: utf-8 -*-
# mcp_servers/code_analyzer/server.py — FastMCP-инстанс code_analyzer-сервера
#
# Создаёт инстанс FastMCP и импортирует tools,
# чтобы декораторы @mcp.tool() зарегистрировали инструменты.

from fastmcp import FastMCP

mcp = FastMCP(
    "code-analyzer",
    instructions="Static code analysis: scan projects, query symbols, build call graphs",
    version="1.0.0",
)

# Импорт tools для регистрации инструментов
import mcp_servers.code_analyzer.tools  # noqa: F401