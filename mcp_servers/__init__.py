# -*- coding: utf-8 -*-
# mcp_servers/__init__.py — MCP-серверы проекта ai-agent
#
# Содержит modular-архитектуру для всех MCP-серверов.
#
# Текущие серверы:
#   - filesystem/ — файловые операции (read, write, list, search, stat, grep)
#   - fetch/      — веб-запросы (fetch_url, fetch_markdown)
#
# Запуск:
#   python -m mcp_servers.filesystem  # stdio
#   python -m mcp_servers.fetch --transport sse --port 3200

__version__ = "1.0.0"