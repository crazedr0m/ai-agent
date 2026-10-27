# -*- coding: utf-8 -*-
# mcp_servers/code_analyzer/cross_ref_tools.py — Кроссязыковые инструменты

import json
import os

from mcp_servers.code_analyzer.server import mcp
from mcp_servers.code_analyzer.core import _get_all_files
from mcp_servers.code_analyzer.languages import (
    get_analyzer,
    get_supported_languages,
)
from mcp_servers.code_analyzer.cross_language.php_js_bridge import (
    analyze_php_to_js,
    scan_project_php_to_js,
)


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