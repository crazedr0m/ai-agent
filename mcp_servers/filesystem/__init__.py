# -*- coding: utf-8 -*-
# mcp_servers/filesystem/__init__.py — Filesystem MCP-сервер
#
# modular-архитектура:
#   server.py  — FastMCP-инстанс + импорт tools
#   tools.py   — 6 инструментов с @mcp.tool()
#   helpers.py — вспомогательные функции
#
# Запуск:
#   python -m mcp_servers.filesystem           # stdio
#   python -m mcp_servers.filesystem --transport sse --port 3100

import argparse

from mcp_servers.filesystem.server import mcp

# Re-export для тестов и внешнего импорта
from mcp_servers.filesystem.tools import (  # noqa: F401
    read_file,
    write_file,
    list_dir,
    search_files,
    stat_file,
    grep_code,
)


def main():
    """Точка входа: парсит аргументы и запускает сервер."""
    parser = argparse.ArgumentParser(description="Filesystem MCP Server")
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio")
    parser.add_argument("--port", type=int, default=3100)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    if args.transport == "sse":
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()