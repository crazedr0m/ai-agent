# -*- coding: utf-8 -*-
# mcp_servers/substrate/__init__.py — LOG16 Substrate MCP-сервер
#
# modular-архитектура:
#   server.py  — FastMCP-инстанс
#   tools.py   — write_to_substrate, query_substrate, equalize_memory
#   helpers.py — MemoryNode, LOG16 engine
#
# Запуск:
#   python -m mcp_servers.substrate           # stdio
#   python -m mcp_servers.substrate --transport sse --port 3500

import argparse

from mcp_servers.substrate.server import mcp

from mcp_servers.substrate.tools import (  # noqa: F401
    write_to_substrate,
    query_substrate,
    equalize_memory,
)

__all__ = [
    "write_to_substrate",
    "query_substrate",
    "equalize_memory",
]


def main():
    parser = argparse.ArgumentParser(description="LOG16 Substrate MCP Server")
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