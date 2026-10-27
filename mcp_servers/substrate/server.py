# -*- coding: utf-8 -*-
# mcp_servers/substrate/server.py — FastMCP-инстанс substrate-сервера (LOG16)

from fastmcp import FastMCP

mcp = FastMCP(
    "substrate",
    instructions="LOG16 multi-frequency associative memory: write, query, equalize, status",
    version="1.0.0",
)

import mcp_servers.substrate.tools  # noqa: F401