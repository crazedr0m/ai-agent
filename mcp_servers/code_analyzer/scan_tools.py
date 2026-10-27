# -*- coding: utf-8 -*-
# mcp_servers/code_analyzer/scan_tools.py — Инструменты сканирования

import json
import os

from mcp_servers.code_analyzer.server import mcp
from mcp_servers.code_analyzer.core import _clear_cache, _get_all_files
from mcp_servers.code_analyzer.languages import (
    get_analyzer,
    get_supported_languages,
    infer_language,
)
from mcp_servers.code_analyzer.languages.php.procedural import (
    analyze_procedural_file,
    scan_procedural_project,
)
from mcp_servers.code_analyzer.tool_helpers import _resolve_analyzer


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
def scan_procedural_php(project_path: str) -> str:
    """Сканировать PHP-проект на предмет процедурного (легаси) кода.

    Находит PHP-файлы без функций/классов, анализирует top-level statements:
    echo, include/require, extract(), $_GET/$_POST, inline HTML, jQuery.

    Args:
        project_path: корневая директория проекта
    """
    result = scan_procedural_project(project_path)
    return json.dumps(result, indent=2, ensure_ascii=False)