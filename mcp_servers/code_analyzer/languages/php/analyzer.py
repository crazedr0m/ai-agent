# -*- coding: utf-8 -*-
# mcp_servers/code_analyzer/languages/php/analyzer.py — PHP-анализатор
#
# Tree-sitter PHP AST:
#   - function_definition      → name, body (compound_statement), parameters (formal_parameters), return_type (primitive_type)
#   - method_declaration       → name, body, parameters, visibility_modifier
#   - class_declaration        → name, body (declaration_list)
#   - function_call_expression → function (name), arguments
#   - echo_statement           → expression (encapsed_string, string, variable, ...)
#   - include_expression       → include/require + string
#   - encapsed_string          → "..." с интерполяцией
#   - string_content           → текст внутри строки

import tree_sitter_php

from mcp_servers.code_analyzer.core import _get_text, _parse_file
from mcp_servers.code_analyzer.languages.base import BaseAnalyzer
from mcp_servers.code_analyzer.languages import register


class PhpAnalyzer(BaseAnalyzer):
    language = "php"
    function_node_type = "function_definition"
    method_node_type = "method_declaration"
    class_node_type = "class_declaration"
    call_node_type = "function_call_expression"
    import_node_types = ("include_expression", "include_once_expression",
                         "require_expression", "require_once_expression")
    name_field = "name"
    interface_node_type = None

    @property
    def language_lib(self):
        return tree_sitter_php.language_php

    def _walk_node(self, node, code, result, current_function=None):
        """Рекурсивный обход PHP AST."""
        # Функции
        if node.type == "function_definition":
            name_node = node.child_by_field_name("name")
            if name_node:
                func_name = _get_text(name_node, code)
                result["functions"].append({
                    "name": func_name,
                    "start_line": node.start_point[0] + 1,
                    "end_line": node.end_point[0] + 1,
                    "start_byte": node.start_byte,
                    "end_byte": node.end_byte,
                })

        # Методы класса
        elif node.type == "method_declaration":
            name_node = node.child_by_field_name("name")
            if name_node:
                func_name = _get_text(name_node, code)
                result["functions"].append({
                    "name": func_name,
                    "start_line": node.start_point[0] + 1,
                    "end_line": node.end_point[0] + 1,
                    "start_byte": node.start_byte,
                    "end_byte": node.end_byte,
                })

        # Классы
        elif node.type == "class_declaration":
            name_node = node.child_by_field_name("name")
            if name_node:
                result["classes"].append({
                    "name": _get_text(name_node, code),
                    "start_line": node.start_point[0] + 1,
                    "end_line": node.end_point[0] + 1,
                })

        # Импорты (include/require)
        elif node.type in self.import_node_types:
            result["imports"].append(_get_text(node, code))

        # Вызовы функций
        elif node.type == "function_call_expression" and current_function:
            func_node = node.child_by_field_name("function")
            if func_node:
                result["calls"].append({
                    "name": _get_text(func_node, code),
                    "line": node.start_point[0] + 1,
                })

        for child in node.children:
            self._walk_node(child, code, result, current_function)

    def collect_definitions(self, filepath: str) -> dict:
        parsed = _parse_file(filepath, self._parser)
        if parsed is None:
            return {"functions": [], "classes": [], "imports": [], "calls": []}

        root = parsed["root"]
        code = parsed["code"]
        result = {"functions": [], "classes": [], "imports": [], "calls": []}
        self._walk_node(root, code, result)
        return result

    def get_symbol_signature(self, filepath: str, symbol_name: str) -> dict | None:
        parsed = _parse_file(filepath, self._parser)
        if parsed is None:
            return None

        root = parsed["root"]
        code = parsed["code"]

        def find_func(node):
            if node.type in ("function_definition", "method_declaration"):
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
                if child.type == "simple_parameter":
                    pname_node = child.child_by_field_name("variable_name")
                    ptype_node = child.child_by_field_name("type")
                    # В PHP tree-sitter: variable_name содержит $name
                    # type может быть primitive_type (int, string) или named_type (ClassName)
                    params.append({
                        "name": _get_text(pname_node, code) if pname_node else "?",
                        "type": _get_text(ptype_node, code) if ptype_node else None,
                    })

        return_type = None
        if return_type_node:
            return_type = _get_text(return_type_node, code)

        return {
            "name": name,
            "params": params,
            "return_type": return_type,
            "docstring": None,  # В PHP нет docstring в AST
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
            if node.type in ("function_definition", "method_declaration"):
                name_node = node.child_by_field_name("name")
                current_function = _get_text(name_node, code) if name_node else None
                if current_function:
                    graph[current_function] = []

            elif node.type == "function_call_expression" and current_function:
                func_node = node.child_by_field_name("function")
                if func_node:
                    callee = _get_text(func_node, code)
                    graph[current_function].append(callee)

            for child in node.children:
                walk(child, current_function)

        walk(root)
        return graph


# Регистрируем анализатор при импорте модуля
register("php", PhpAnalyzer)