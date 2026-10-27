# -*- coding: utf-8 -*-
# mcp_servers/code_analyzer/query_tools.py — Инструменты запросов к одному файлу

import json

from mcp_servers.code_analyzer.server import mcp
from mcp_servers.code_analyzer.tool_helpers import _resolve_analyzer


@mcp.tool()
def query_function(
    file_path: str,
    function_name: str,
    language: str | None = None,
) -> str:
    """Найти функцию и её контекст: сигнатура, тело, callers, callees.

    Args:
        file_path: путь к файлу
        function_name: имя функции
        language: язык (определяется автоматически по расширению, если не указан)
    """
    analyzer, error = _resolve_analyzer(file_path, language)
    if error:
        return error

    sig = analyzer.get_symbol_signature(file_path, function_name)
    if sig is None:
        return f"Ошибка: функция '{function_name}' не найдена в '{file_path}'"

    graph = analyzer.build_call_graph(file_path)
    callees = graph.get(function_name, [])
    callers = [
        caller for caller, callee_list in graph.items()
        if function_name in callee_list
    ]

    result = {
        "signature": sig,
        "callers": callers,
        "callees": callees,
    }

    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def query_callers(
    file_path: str,
    function_name: str,
    language: str | None = None,
) -> str:
    """Кто вызывает функцию.

    Args:
        file_path: путь к файлу
        function_name: имя функции
        language: язык (определяется автоматически по расширению, если не указан)
    """
    analyzer, error = _resolve_analyzer(file_path, language)
    if error:
        return error

    graph = analyzer.build_call_graph(file_path)
    callers = [
        caller for caller, callee_list in graph.items()
        if function_name in callee_list
    ]

    if not callers:
        return f"Функцию '{function_name}' никто не вызывает в этом файле"

    return json.dumps({
        "function": function_name,
        "file": file_path,
        "callers": callers,
    }, indent=2, ensure_ascii=False)


@mcp.tool()
def query_callees(
    file_path: str,
    function_name: str,
    language: str | None = None,
) -> str:
    """Кого вызывает функция.

    Args:
        file_path: путь к файлу
        function_name: имя функции
        language: язык (определяется автоматически по расширению, если не указан)
    """
    analyzer, error = _resolve_analyzer(file_path, language)
    if error:
        return error

    graph = analyzer.build_call_graph(file_path)
    callees = graph.get(function_name, [])

    if not callees:
        return f"Функция '{function_name}' ничего не вызывает в этом файле"

    return json.dumps({
        "function": function_name,
        "file": file_path,
        "callees": callees,
    }, indent=2, ensure_ascii=False)