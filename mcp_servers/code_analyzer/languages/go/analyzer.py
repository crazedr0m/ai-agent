# -*- coding: utf-8 -*-
# mcp_servers/code_analyzer/languages/go/analyzer.py — Go-анализатор
#
# Tree-sitter Go AST:
#   - source_file                → корневой узел
#   - function_declaration       → name (identifier), parameters (parameter_list),
#                                   result (type_identifier), body (block)
#   - method_declaration         → receiver (parameter_list), name (field_identifier),
#                                   parameters (parameter_list), result, body
#   - type_declaration           → type_spec → name (type_identifier), type
#   - call_expression            → function (identifier/selector_expression), arguments
#   - import_declaration         → import_spec_list → import_spec → interpreted_string_literal
#   - const_declaration          → const_spec → name (identifier), value (expression_list)
#   - parameter_declaration      → name (identifier), type (type_identifier)
#   - selector_expression        → operand (identifier) + . + field_identifier (selector)

import tree_sitter_go

from mcp_servers.code_analyzer.core import _get_text, _parse_file
from mcp_servers.code_analyzer.languages.base import BaseAnalyzer
from mcp_servers.code_analyzer.languages import register


class GoAnalyzer(BaseAnalyzer):
    language = "go"
    function_node_type = "function_declaration"
    method_node_type = "method_declaration"
    class_node_type = "type_declaration"
    call_node_type = "call_expression"
    import_node_types = ("import_declaration",)
    name_field = "name"
    interface_node_type = None

    @property
    def language_lib(self):
        return tree_sitter_go.language

    def collect_definitions(self, filepath: str) -> dict:
        parsed = _parse_file(filepath, self._parser)
        if parsed is None:
            return {"functions": [], "classes": [], "imports": [], "calls": []}

        root = parsed["root"]
        code = parsed["code"]
        result = {"functions": [], "classes": [], "imports": [], "calls": []}

        def walk(node):
            # Function declarations: func foo() {}
            if node.type == "function_declaration":
                name_node = node.child_by_field_name("name")
                result["functions"].append({
                    "name": _get_text(name_node, code) if name_node else "<anon>",
                    "start_line": node.start_point[0] + 1,
                    "end_line": node.end_point[0] + 1,
                    "start_byte": node.start_byte,
                    "end_byte": node.end_byte,
                })

            # Method declarations: func (r *T) Method() {}
            elif node.type == "method_declaration":
                name_node = node.child_by_field_name("name")
                result["functions"].append({
                    "name": _get_text(name_node, code) if name_node else "<anon>",
                    "start_line": node.start_point[0] + 1,
                    "end_line": node.end_point[0] + 1,
                    "start_byte": node.start_byte,
                    "end_byte": node.end_byte,
                })

            # Type declarations: type Foo struct {}
            # We map Go types as "classes" for compatibility
            elif node.type == "type_declaration":
                for child in node.children:
                    if child.type == "type_spec":
                        name_node = child.child_by_field_name("name")
                        if name_node:
                            result["classes"].append({
                                "name": _get_text(name_node, code),
                                "start_line": node.start_point[0] + 1,
                                "end_line": node.end_point[0] + 1,
                            })

            # Imports: import "fmt" / import ("fmt"; "os")
            elif node.type in self.import_node_types:
                result["imports"].append(_get_text(node, code))

            # Function calls: foo() or pkg.Func()
            elif node.type == "call_expression":
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
            if node.type in ("function_declaration", "method_declaration"):
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
        return_type_node = func_node.child_by_field_name("result")

        name = _get_text(name_node, code) if name_node else symbol_name

        params = []
        if params_node:
            for child in params_node.children:
                if child.type == "parameter_declaration":
                    pname_node = child.child_by_field_name("name")
                    ptype_node = child.child_by_field_name("type")
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
            "docstring": None,  # В Go нет docstring в AST
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
            if node.type == "function_declaration":
                name_node = node.child_by_field_name("name")
                current_function = _get_text(name_node, code) if name_node else None
                if current_function:
                    graph[current_function] = []

            elif node.type == "method_declaration":
                name_node = node.child_by_field_name("name")
                current_function = _get_text(name_node, code) if name_node else None
                if current_function:
                    graph[current_function] = []

            elif node.type == "call_expression" and current_function:
                func_node = node.child_by_field_name("function")
                if func_node:
                    callee = _get_text(func_node, code)
                    graph[current_function].append(callee)

            for child in node.children:
                walk(child, current_function)

        walk(root)
        return graph


# Регистрируем анализатор при импорте модуля
register("go", GoAnalyzer)