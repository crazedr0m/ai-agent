# -*- coding: utf-8 -*-
# mcp_servers/code_analyzer/tools.py — Facade: реэкспорт из модульных файлов
#
# После рефакторинга:
#   scan_tools.py       — scan_project, scan_procedural_php
#   query_tools.py      — query_function, query_callers, query_callees
#   cross_ref_tools.py  — query_cross_references, query_js_from_php, scan_php_js_project
#   tool_helpers.py     — _resolve_analyzer

# Импортируем всё, чтобы MCP-инструменты зарегистрировались
from mcp_servers.code_analyzer.scan_tools import scan_project, scan_procedural_php  # noqa: F401
from mcp_servers.code_analyzer.query_tools import query_function, query_callers, query_callees  # noqa: F401
from mcp_servers.code_analyzer.cross_ref_tools import query_cross_references, query_js_from_php, scan_php_js_project  # noqa: F401
from mcp_servers.code_analyzer.tool_helpers import _resolve_analyzer  # noqa: F401