# -*- coding: utf-8 -*-
# mcp_servers/fractional_memory/__init__.py — Сервер дробно-слойной памяти
#
# modular-архитектура:
#   server.py  — FastMCP-инстанс
#   tools.py   — write_fact, query_facts, consolidate_memory
#   helpers.py — MemoryNode, дробно-логарифмический движок полос
#
# Запуск:
#   python -m mcp_servers.fractional_memory           # stdio
#   python -m mcp_servers.fractional_memory --transport sse --port 3500

import argparse

from mcp_servers.fractional_memory.server import mcp

from mcp_servers.fractional_memory.tools import (  # noqa: F401
    write_fact,
    query_facts,
    consolidate_memory,
)

__all__ = [
    "write_fact",
    "query_facts",
    "consolidate_memory",
]


def main():
    parser = argparse.ArgumentParser(description="Fractional Memory MCP Server")
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio")
    parser.add_argument("--port", type=int, default=3500)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    if args.transport == "sse":
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
