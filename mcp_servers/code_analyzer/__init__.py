# -*- coding: utf-8 -*-
# mcp_servers/code_analyzer/__init__.py — Code Analyzer MCP-сервер
#
# modular-архитектура:
#   server.py  — FastMCP-инстанс + импорт tools
#   tools.py   — инструменты с @mcp.tool()
#   helpers.py — вспомогательные функции (кэш, обход AST)
#
# Запуск:
#   python -m mcp_servers.code_analyzer           # stdio
#   python -m mcp_servers.code_analyzer --transport sse --port 3400

import argparse

from mcp_servers.code_analyzer.server import mcp

# Re-export для тестов и внешнего импорта
from mcp_servers.code_analyzer.tools import (  # noqa: F401
    scan_project,
    query_function,
    query_callers,
    query_callees,
)

__all__ = [
    "scan_project",
    "query_function",
    "query_callers",
    "query_callees",
]


def main():
    """Точка входа: парсит аргументы и запускает сервер."""
    parser = argparse.ArgumentParser(description="Code Analyzer MCP Server")
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio")
    parser.add_argument("--port", type=int, default=3400)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    if args.transport == "sse":
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()