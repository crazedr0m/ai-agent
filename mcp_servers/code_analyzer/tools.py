# -*- coding: utf-8 -*-
# mcp_servers/code_analyzer/tools.py — Инструменты анализатора кода
#
# 8 инструментов:
#   - scan_project              — полное сканирование проекта (все языки)
#   - query_function            — сигнатура + тело + кто вызывает + кого вызывает
#   - query_callers             — кто вызывает функцию
#   - query_callees             — кого вызывает функция
#   - query_cross_references    — поиск символа во всех языках проекта
#   - query_js_from_php         — PHP→JS кроссязыковый анализ (один файл)
#   - scan_php_js_project       — PHP→JS сканирование всего проекта
#   - scan_procedural_php       — анализ процедурного (легаси) PHP кода
#
# Не содержит логики обхода AST — делегирует языковым модулям через ParserRegistry.

import json
import os

from mcp_servers.code_analyzer.server import mcp
from mcp_servers.code_analyzer.core import _clear_cache, _get_all_files
from mcp_servers.code_analyzer.languages import (
    get_analyzer,
    get_supported_languages,
    infer_language,
)
from mcp_servers.code_analyzer.cross_language.php_js_bridge import (
    analyze_php_to_js,
    scan_project_php_to_js,
)
from mcp_servers.code_analyzer.languages.php.procedural import (
    analyze_procedural_file,
    scan_procedural_project,
)


def _resolve_analyzer(file_path: str, language: str | None = None) -> tuple:
    """Определить анализатор по языку или расширению файла.

    Returns:
        (BaseAnalyzer | None, str | None) — (анализатор, сообщение об ошибке)
    """
    if language is None:
        language = infer_language(file_path)
        if language is None:
            return None, f"Не удалось определить язык для '{file_path}'"

    analyzer = get_analyzer(language)
    if analyzer is None:
        supported = ", ".join(get_supported_languages())
        return None, f"Язык '{language}' не поддерживается. Поддерживаются: {supported}"

    return analyzer, None


# ── MCP-инструменты ──────────────────────────────────────────────


@mcp.tool()
def scan_project(root_path: str, language: str | None = None) -> str:
    """Полное сканирование проекта: функции, классы, импорты, граф вызовов.

    Если language не указан — сканируются все поддерживаемые языки.
    Если language указан — сканируются только файлы этого языка.

    Args:
        root_path: корневая директория проекта
        language: язык для сканирования (например "python", "php", "js"),
                  или None для всех языков
    """
    if not os.path.isdir(root_path):
        return f"Ошибка: папка '{root_path}' не найдена"

    _clear_cache()

    if language:
        languages_to_scan = [language]
    else:
        languages_to_scan = get_supported_languages()

    all_functions = []
    all_classes = []
    all_imports = []
    call_graph: dict[str, list[str]] = {}
    file_index: dict[str, list[str]] = {}
    total_files = 0

    for lang in languages_to_scan:
        analyzer = get_analyzer(lang)
        if analyzer is None:
            continue

        # Определяем расширение по языку
        ext_map = {
            "python": ".py",
            "php": ".php",
            "javascript": ".js",
            "typescript": ".ts",
            "go": ".go",
        }
        ext = ext_map.get(lang, ".txt")
        files = _get_all_files(root_path, extension=ext)

        for fp in files:
            rel = os.path.relpath(fp, root_path)
            defs = analyzer.collect_definitions(fp)

            for fn in defs["functions"]:
                fn["file"] = rel
                fn["language"] = lang
                all_functions.append(fn)

            for cls in defs["classes"]:
                cls["file"] = rel
                cls["language"] = lang
                all_classes.append(cls)

            all_imports.extend({
                "file": rel,
                "language": lang,
                "statement": imp,
            } for imp in defs["imports"])

            fg = analyzer.build_call_graph(fp)
            for caller, callees in fg.items():
                if caller not in call_graph:
                    call_graph[caller] = []
                call_graph[caller].extend(callees)

            file_index[rel] = [fn["name"] for fn in defs["functions"]]
            total_files += 1

    summary = {
        "files_scanned": total_files,
        "total_functions": len(all_functions),
        "total_classes": len(all_classes),
        "total_imports": len(all_imports),
        "languages": languages_to_scan,
    }

    result = {
        "summary": summary,
        "functions": all_functions,
        "classes": all_classes,
        "imports": all_imports[:200],
        "call_graph": {k: list(set(v)) for k, v in call_graph.items()},
        "file_index": file_index,
    }

    return json.dumps(result, indent=2, ensure_ascii=False)


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


@mcp.tool()
def query_cross_references(symbol_name: str, project_path: str) -> str:
    """Найти все вхождения символа во всех языках проекта.

    Args:
        symbol_name: имя символа (функции/класса)
        project_path: корневая директория проекта
    """
    if not os.path.isdir(project_path):
        return f"Ошибка: папка '{project_path}' не найдена"

    results = []

    for lang in get_supported_languages():
        analyzer = get_analyzer(lang)
        if analyzer is None:
            continue

        ext_map = {
            "python": ".py",
            "php": ".php",
            "javascript": ".js",
            "typescript": ".ts",
            "go": ".go",
        }
        ext = ext_map.get(lang, ".txt")
        files = _get_all_files(project_path, extension=ext)

        for fp in files:
            sig = analyzer.get_symbol_signature(fp, symbol_name)
            if sig:
                rel = os.path.relpath(fp, project_path)
                results.append({
                    "language": lang,
                    "file": rel,
                    "type": "definition",
                    "signature": sig,
                })

            # Ищем вызовы
            graph = analyzer.build_call_graph(fp)
            for caller, callees in graph.items():
                if symbol_name in callees:
                    rel = os.path.relpath(fp, project_path)
                    results.append({
                        "language": lang,
                        "file": rel,
                        "type": "caller",
                        "caller": caller,
                    })

    if not results:
        return f"Символ '{symbol_name}' не найден в проекте '{project_path}'"

    return json.dumps({
        "symbol": symbol_name,
        "project": project_path,
        "occurrences": results,
    }, indent=2, ensure_ascii=False)


# ── Кроссязыковые инструменты ─────────────────────────────────────


@mcp.tool()
def query_js_from_php(php_file_path: str, project_path: str) -> str:
    """Проанализировать PHP-файл на предмет генерации JS-кода в строках.

    Анализирует цепочку: PHP (echo/print/строки) → HTML → <script>/inline-JS
    → поиск определений JS-символов в .js/.ts файлах.

    Args:
        php_file_path: путь к PHP-файлу
        project_path: корневая директория проекта (для поиска .js/.ts)
    """
    result = analyze_php_to_js(php_file_path, project_path)
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def scan_php_js_project(project_path: str) -> str:
    """Сканировать весь проект на PHP→JS кроссязыковые связи.

    Находит все PHP-файлы, генерирующие JS-код через строковые литералы,
    и связывает их с определениями в .js/.ts файлах.

    Args:
        project_path: корневая директория проекта
    """
    results = scan_project_php_to_js(project_path)
    if not results:
        return json.dumps({
            "message": f"PHP→JS связи не найдены в '{project_path}'",
            "files_with_js": 0,
        }, indent=2, ensure_ascii=False)

    total_js_fragments = sum(
        r["summary"]["js_fragments_found"] for r in results
    )
    total_resolved = sum(
        r["summary"]["resolved_in_js_files"] for r in results
    )

    return json.dumps({
        "php_files_with_js": len(results),
        "total_js_fragments": total_js_fragments,
        "total_resolved_symbols": total_resolved,
        "details": results,
    }, indent=2, ensure_ascii=False)


@mcp.tool()
def scan_procedural_php(project_path: str) -> str:
    """Сканировать PHP-проект на предмет процедурного (легаси) кода.

    Находит PHP-файлы без функций/классов, анализирует top-level statements:
    echo, include/require, extract(), $_GET/$_POST, inline HTML, jQuery.

    Args:
        project_path: корневая директория проекта
    """
    result = scan_procedural_project(project_path)
    return json.dumps(result, indent=2, ensure_ascii=False)