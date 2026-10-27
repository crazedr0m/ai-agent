# -*- coding: utf-8 -*-
# mcp_servers/code_analyzer/languages/python/analyzer.py — Python-анализатор

import tree_sitter_python

from mcp_servers.code_analyzer.core import _get_text, _parse_file
from mcp_servers.code_analyzer.languages.base import BaseAnalyzer
from mcp_servers.code_analyzer.languages import register


class PythonAnalyzer(BaseAnalyzer):
    language = "python"
    function_node_type = "function_definition"
    method_node_type = "method_definition"
    class_node_type = "class_definition"
    call_node_type = "call"
    import_node_types = ("import_statement", "import_from_statement")
    name_field = "name"
    interface_node_type = None

    @property
    def language_lib(self):
        return tree_sitter_python.language

    def collect_definitions(self, filepath: str) -> dict:
        parsed = _parse_file(filepath, self._parser)
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
            elif node.type in ("import_statement", "import_from_statement"):
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

    def get_symbol_signature(self, filepath: str, symbol_name: str) -> dict | None:
        parsed = _parse_file(filepath, self._parser)
        if parsed is None:
            return None

        root = parsed["root"]
        code = parsed["code"]

        def find_func(node):
            if node.type == "function_definition":
                name_node = node.child_by_field_name("name")
                if name_node and _get_text(name_node, code) == symbol_name:
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

        name = _get_text(name_node, code) if name_node else symbol_name

        params = []
        if params_node:
            for child in params_node.children:
                if child.type == "typed_parameter":
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

    def build_call_graph(self, filepath: str) -> dict[str, list[str]]:
        parsed = _parse_file(filepath, self._parser)
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


# Регистрируем анализатор при импорте модуля
register("python", PythonAnalyzer)