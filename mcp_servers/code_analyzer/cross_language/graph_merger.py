# -*- coding: utf-8 -*-
# mcp_servers/code_analyzer/cross_language/graph_merger.py
#
# Graph Merger — объединение графов вызовов из разных языков.
#
# Сливает графы из PHP, JS, Python, Go в единый кроссязыковый граф,
# помечая каждый узел и ребро языком-источником.

from collections import defaultdict


def merge_call_graphs(
    php_graph: dict[str, list[str]],
    js_graph: dict[str, list[str]],
    ts_graph: dict[str, list[str]] | None = None,
    py_graph: dict[str, list[str]] | None = None,
    go_graph: dict[str, list[str]] | None = None,
) -> dict:
    """Объединить графы вызовов из разных языков.

    Args:
        php_graph: граф из PHP-анализатора
        js_graph: граф из JS-анализатора
        ts_graph: граф из TS-анализатора (опционально)
        py_graph: граф из Python-анализатора (опционально)
        go_graph: граф из Go-анализатора (опционально)

    Returns:
        {
            "nodes": { "func_name": {"languages": ["php", "js"], "file": "..."} },
            "edges": [
                {"caller": "...", "callee": "...", "caller_language": "php", "callee_language": "js"}
            ],
            "cross_language_calls": [...]
        }
    """
    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    # Мета-информация о файлах для каждого языка
    # В реальности нужно передавать file_map из сканера
    # Здесь — упрощённая версия без привязки к файлам

    source_graphs = {
        "php": php_graph,
        "javascript": js_graph,
        "typescript": ts_graph or {},
        "python": py_graph or {},
        "go": go_graph or {},
    }

    for lang, graph in source_graphs.items():
        for caller, callees in graph.items():
            # Регистрируем caller
            if caller not in nodes:
                nodes[caller] = {"languages": set(), "files": []}
            nodes[caller]["languages"].add(lang)

            for callee in callees:
                # Регистрируем callee
                if callee not in nodes:
                    nodes[callee] = {"languages": set(), "files": []}
                # Пытаемся определить язык callee по его присутствию в других графах
                callee_lang = _infer_callee_language(callee, source_graphs, lang)

                nodes[callee]["languages"].add(callee_lang)

                edges.append({
                    "caller": caller,
                    "callee": callee,
                    "caller_language": lang,
                    "callee_language": callee_lang,
                })

    cross_language = [
        e for e in edges if e["caller_language"] != e["callee_language"]
    ]

    return {
        "nodes": {
            name: {
                "languages": sorted(list(info["languages"])),
                "files": info["files"],
            }
            for name, info in nodes.items()
        },
        "edges": edges,
        "cross_language_calls": cross_language,
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "total_cross_language": len(cross_language),
    }


def _infer_callee_language(
    callee: str,
    source_graphs: dict[str, dict[str, list[str]]],
    caller_lang: str,
) -> str:
    """Пытается определить язык callee по графам.

    Если callee определён как caller в другом языке — возвращаем его.
    Иначе возвращаем язык caller (по умолчанию внутриязыковый вызов).
    """
    for lang, graph in source_graphs.items():
        if callee in graph:
            return lang
    return caller_lang


def format_merged_graph(merged: dict) -> str:
    """Форматировать объединённый граф для вывода через MCP."""
    import json

    output = {
        "summary": {
            "total_nodes": merged["total_nodes"],
            "total_edges": merged["total_edges"],
            "cross_language_calls": merged["total_cross_language"],
        },
        "cross_language_calls": [
            {
                "from": f"[{e['caller_language']}] {e['caller']}",
                "to": f"[{e['callee_language']}] {e['callee']}",
            }
            for e in merged["cross_language_calls"]
        ],
        "all_edges": [
            {
                "from": f"[{e['caller_language']}] {e['caller']}",
                "to": f"[{e['callee_language']}] {e['callee']}",
            }
            for e in merged["edges"]
        ],
    }

    return json.dumps(output, indent=2, ensure_ascii=False)



# ── Функция для быстрого тестирования ────────────────────────────


def _demo():
    """Демонстрация работы graph_merger."""
    php_graph = {
        "renderPage": ["getUserData", "json_encode", "include_template"],
        "getUserData": ["query_db"],
    }
    js_graph = {
        "initPage": ["fetchData", "renderUI"],
        "fetchData": ["callApi"],
        "renderUI": ["updateDOM"],
    }

    merged = merge_call_graphs(php_graph, js_graph)
    print(format_merged_graph(merged))


if __name__ == "__main__":
    _demo()