# -*- coding: utf-8 -*-
# mcp_servers/fetch/__main__.py — Точка входа для python -m
#
# Перенаправляем stderr в /dev/null, чтобы FastMCP-баннеры
# не засоряли родительский терминал (особенно curses/TUI).

import os
import sys

sys.stderr = open(os.devnull, "w", encoding="utf-8")

from mcp_servers.fetch import main  # noqa: E402

main()