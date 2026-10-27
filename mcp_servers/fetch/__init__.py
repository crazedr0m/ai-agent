# -*- coding: utf-8 -*-
# mcp_servers/fetch/__init__.py — Web Fetch MCP-сервер
#
# modular-архитектура:
#   server.py       — FastMCP-инстанс + импорт tools
#   tools.py        — 2 инструмента с @mcp.tool()
#   html_converter.py — конвертер HTML → упрощённый Markdown
#
# Запуск:
#   python -m mcp_servers.fetch           # stdio
#   python -m mcp_servers.fetch --transport sse --port 3200

import argparse

from mcp_servers.fetch.server import mcp

# Re-export для тестов и внешнего импорта
from mcp_servers.fetch.tools import fetch_url, fetch_markdown  # noqa: F401


def main():
    """Точка входа: парсит аргументы и запускает сервер."""
    parser = argparse.ArgumentParser(description="Web Fetch MCP Server")
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio")
    parser.add_argument("--port", type=int, default=3200)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    if args.transport == "sse":
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()