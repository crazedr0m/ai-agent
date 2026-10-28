# -*- coding: utf-8 -*-
# mcp_servers/fractional_memory/server.py — FastMCP-инстанс сервера дробно-слойной памяти

from fastmcp import FastMCP

mcp = FastMCP(
    "fractional_memory",
    instructions="Fractional layered memory: multi-band associative facts with fractional decay. write, query, consolidate, status",
    version="1.0.0",
)

import mcp_servers.fractional_memory.tools  # noqa: F401
