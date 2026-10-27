# -*- coding: utf-8 -*-
# mcp_servers/code_analyzer/tools.py — Инструменты анализатора кода
#
# 4 инструмента:
#   - scan_project     — полное сканирование проекта, возвращает граф
#   - query_function   — сигнатура + тело + кто вызывает + кого вызывает
#   - query_callers    — кто вызывает функцию
#   - query_callees    — кого вызывает функция
#
# Базируется на Tree-sitter Python API.

import os
import json
from typing import Optional

from tree_sitter import Language, Parser
import tree_sitter_python

from mcp_servers.code_analyzer.server import mcp

# ── Инициализация парсера (один раз) ─────────────────────────────
_LANGUAGE = Language(tree_sitter_python.language())
_PARSER = Parser(_LANGUAGE)

# ── Кэш AST ──────────────────────────────────────────────────────
_ast_cache: dict[str, dict] = {}


def _parse_file(filepath: str) -> dict | None:
    """Распарсить файл, вернуть AST-структуру (с кэшированием)."""
    if filepath in _ast_cache:
        return _ast_cache[filepath]

    if not os.path.isfile(filepath):
        return None

    try:
        with open(filepath, "rb") as f:
            code = f.read()
    except Exception:
        return None

    tree = _PARSER.parse(code)
    _ast_cache[filepath] = {
        "tree": tree,
        "code": code.decode("utf-8", errors="replace"),
        "root": tree.root_node,
    }
    return _ast_cache[filepath]


def _clear_cache():
    """Сбросить кэш AST (для тестов и принудительного пересканирования)."""
    _ast_cache.clear()


# ── Внутренние структуры ─────────────────────────────────────────


def _get_text(node, code: str) -> str:
    """Извлечь текст узла AST из исходного кода."""
    return code[node.start_byte:node.end_byte]


def _collect_definitions(filepath: str) -> dict:
    """Собрать все функции, классы, импорты, вызовы из файла."""
    parsed = _parse_file(filepath)
    if parsed is None:
        return {"functions": [], "classes": [], "imports": [], "calls": []}

    root = parsed["root"]
    code = parsed["code"]
    result = {"functions": [], "classes": [], "imports": [], "calls": []}

    def walk(node):
        if node.type == "function_definition":
            name_node = node.child_by_field_name("name")
            result["functions"].append({
                "name": _get_text(name_node, code) if name_node else "<anon>",
                "start_line": node.start_point[0] + 1,
                "end_line": node.end_point[0] + 1,
                "start_byte": node.start_byte,
                "end_byte": node.end_byte,
            })
        elif node.type == "class_definition":
            name_node = node.child_by_field_name("name")
            result["classes"].append({
                "name": _get_text(name_node, code) if name_node else "<anon>",
                "start_line": node.start_point[0] + 1,
                "end_line": node.end_point[0] + 1,
            })
        elif node.type == "import_statement":
            result["imports"].append(_get_text(node, code))
        elif node.type == "import_from_statement":
            result["imports"].append(_get_text(node, code))
        elif node.type == "call":
            func_node = node.child_by_field_name("function")
            if func_node:
                result["calls"].append({
                    "name": _get_text(func_node, code),
                    "line": node.start_point[0] + 1,
                })

        for child in node.children:
            walk(child)

    walk(root)
    return result


def _get_function_signature(filepath: str, func_name: str) -> dict | None:
    """Извлечь сигнатуру функции: имя, параметры, return_type, docstring."""
    parsed = _parse_file(filepath)
    if parsed is None:
        return None

    root = parsed["root"]
    code = parsed["code"]

    def find_func(node):
        if node.type == "function_definition":
            name_node = node.child_by_field_name("name")
            if name_node and _get_text(name_node, code) == func_name:
                return node
        for child in node.children:
            result = find_func(child)
            if result:
                return result
        return None

    func_node = find_func(root)
    if not func_node:
        return None

    name_node = func_node.child_by_field_name("name")
    params_node = func_node.child_by_field_name("parameters")
    return_type_node = func_node.child_by_field_name("return_type")

    name = _get_text(name_node, code) if name_node else func_name

    params = []
    if params_node:
        for child in params_node.children:
            if child.type == "typed_parameter":
                # typed_parameter: identifier ":" type
                # tree-sitter-python field names for typed_parameter
                # may use 'name' and 'type' fields; fallback to child iteration
                pname_node = child.child_by_field_name("name")
                ptype_node = child.child_by_field_name("type")
                if pname_node is None:
                    for gc in child.children:
                        if gc.type == "identifier":
                            pname_node = gc
                        elif gc.type == "type":
                            ptype_node = gc
                params.append({
                    "name": _get_text(pname_node, code) if pname_node else "?",
                    "type": _get_text(ptype_node, code) if ptype_node else None,
                })
            elif child.type == "identifier":
                params.append({
                    "name": _get_text(child, code),
                    "type": None,
                })

    return_type = None
    if return_type_node:
        return_type = _get_text(return_type_node, code)

    # Docstring
    body = func_node.child_by_field_name("body")
    docstring = None
    if body and body.children:
        first = body.children[0]
        if first.type == "expression_statement" and first.children:
            expr = first.children[0]
            if expr.type == "string":
                raw = _get_text(expr, code)
                docstring = raw.strip("\"'")

    return {
        "name": name,
        "params": params,
        "return_type": return_type,
        "docstring": docstring,
        "start_line": func_node.start_point[0] + 1,
        "end_line": func_node.end_point[0] + 1,
        "body": _get_text(func_node, code),
    }


def _build_call_graph(filepath: str) -> dict[str, list[str]]:
    """Построить граф вызовов: {caller: [callee, ...]}."""
    parsed = _parse_file(filepath)
    if parsed is None:
        return {}

    root = parsed["root"]
    code = parsed["code"]
    graph: dict[str, list[str]] = {}

    def walk(node, current_function=None):
        if node.type == "function_definition":
            name_node = node.child_by_field_name("name")
            current_function = _get_text(name_node, code) if name_node else None
            if current_function:
                graph[current_function] = []

        if node.type == "call" and current_function:
            func_node = node.child_by_field_name("function")
            if func_node:
                callee = _get_text(func_node, code)
                graph[current_function].append(callee)

        for child in node.children:
            walk(child, current_function)

    walk(root)
    return graph


def _get_all_files(root_path: str, pattern: str = ".py") -> list[str]:
    """Рекурсивно найти все Python-файлы в директории."""
    files = []
    for dirpath, dirnames, filenames in os.walk(root_path):
        # Пропускаем venv, __pycache__, .git
        dirnames[:] = [
            d for d in dirnames
            if not d.startswith(".")
            and d not in ("venv", "__pycache__", "node_modules")
        ]
        for f in filenames:
            if f.endswith(pattern):
                files.append(os.path.join(dirpath, f))
    return sorted(files)


# ── MCP-инструменты ──────────────────────────────────────────────


@mcp.tool()
def scan_project(root_path: str) -> str:
    """Полное сканирование проекта: функции, классы, импорты, граф вызовов.

    Args:
        root_path: корневая директория проекта
    """
    if not os.path.isdir(root_path):
        return f"Ошибка: папка '{root_path}' не найдена"

    _clear_cache()
    py_files = _get_all_files(root_path)

    all_functions = []
    all_classes = []
    all_imports = []
    call_graph: dict[str, list[str]] = {}
    file_index: dict[str, list[str]] = {}

    for fp in py_files:
        rel = os.path.relpath(fp, root_path)
        defs = _collect_definitions(fp)

        for fn in defs["functions"]:
            fn["file"] = rel
            all_functions.append(fn)

        for cls in defs["classes"]:
            cls["file"] = rel
            all_classes.append(cls)

        all_imports.extend({
            "file": rel,
            "statement": imp,
        } for imp in defs["imports"])

        fg = _build_call_graph(fp)
        for caller, callees in fg.items():
            if caller not in call_graph:
                call_graph[caller] = []
            call_graph[caller].extend(callees)

        file_index[rel] = [fn["name"] for fn in defs["functions"]]

    summary = {
        "files_scanned": len(py_files),
        "total_functions": len(all_functions),
        "total_classes": len(all_classes),
        "total_imports": len(all_imports),
    }

    result = {
        "summary": summary,
        "functions": all_functions,
        "classes": all_classes,
        "imports": all_imports[:200],  # ограничение по объёму
        "call_graph": {k: list(set(v)) for k, v in call_graph.items()},
        "file_index": file_index,
    }

    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def query_function(file_path: str, function_name: str) -> str:
    """Найти функцию и её контекст: сигнатура, тело, callers, callees.

    Args:
        file_path: путь к файлу
        function_name: имя функции
    """
    sig = _get_function_signature(file_path, function_name)
    if sig is None:
        return f"Ошибка: функция '{function_name}' не найдена в '{file_path}'"

    # Граф вызовов в этом файле
    graph = _build_call_graph(file_path)
    callees = graph.get(function_name, [])

    # Кто вызывает эту функцию в файле
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
def query_callers(file_path: str, function_name: str) -> str:
    """Кто вызывает функцию.

    Args:
        file_path: путь к файлу
        function_name: имя функции
    """
    graph = _build_call_graph(file_path)
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
def query_callees(file_path: str, function_name: str) -> str:
    """Кого вызывает функция.

    Args:
        file_path: путь к файлу
        function_name: имя функции
    """
    graph = _build_call_graph(file_path)
    callees = graph.get(function_name, [])

    if not callees:
        return f"Функция '{function_name}' ничего не вызывает в этом файле"

    return json.dumps({
        "function": function_name,
        "file": file_path,
        "callees": callees,
    }, indent=2, ensure_ascii=False)