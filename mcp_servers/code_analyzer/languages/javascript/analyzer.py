# -*- coding: utf-8 -*-
# mcp_servers/code_analyzer/languages/javascript/analyzer.py — JavaScript-анализатор
#
# Tree-sitter JavaScript AST:
#   - function_declaration      → name, parameters, body (statement_block)
#   - method_definition         → property_identifier (name), parameters, body
#   - arrow_function            → parameters, body (или expression)
#   - class_declaration         → name, body (class_body)
#   - call_expression           → function (identifier/member_expression), arguments
#   - import_statement          → import_clause + from + source (string)
#   - export_statement          → export + declaration
#   - lexical_declaration       → const/let/var + variable_declarator(s)

import tree_sitter_javascript

from mcp_servers.code_analyzer.core import _get_text, _parse_file
from mcp_servers.code_analyzer.languages.base import BaseAnalyzer
from mcp_servers.code_analyzer.languages import register


class JavaScriptAnalyzer(BaseAnalyzer):
    language = "javascript"
    function_node_type = "function_declaration"
    method_node_type = "method_definition"
    class_node_type = "class_declaration"
    call_node_type = "call_expression"
    import_node_types = ("import_statement",)
    name_field = "name"
    interface_node_type = None

    @property
    def language_lib(self):
        return tree_sitter_javascript.language

    def collect_definitions(self, filepath: str) -> dict:
        parsed = _parse_file(filepath, self._parser)
        if parsed is None:
            return {"functions": [], "classes": [], "imports": [], "calls": []}

        root = parsed["root"]
        code = parsed["code"]
        result = {"functions": [], "classes": [], "imports": [], "calls": []}

        def walk(node):
            # Function declarations: function foo() {}
            if node.type == "function_declaration":
                name_node = node.child_by_field_name("name")
                result["functions"].append({
                    "name": _get_text(name_node, code) if name_node else "<anon>",
                    "start_line": node.start_point[0] + 1,
                    "end_line": node.end_point[0] + 1,
                    "start_byte": node.start_byte,
                    "end_byte": node.end_byte,
                })

            # Methods in classes: { foo() {} }
            elif node.type == "method_definition":
                name_node = node.child_by_field_name("name")
                result["functions"].append({
                    "name": _get_text(name_node, code) if name_node else "<anon>",
                    "start_line": node.start_point[0] + 1,
                    "end_line": node.end_point[0] + 1,
                    "start_byte": node.start_byte,
                    "end_byte": node.end_byte,
                })

            # Arrow functions assigned to variables: const foo = () => {}
            elif node.type == "arrow_function":
                parent = node.parent
                if parent and parent.type == "variable_declarator":
                    name_node = parent.child_by_field_name("name")
                    result["functions"].append({
                        "name": _get_text(name_node, code) if name_node else "<anon>",
                        "start_line": node.start_point[0] + 1,
                        "end_line": node.end_point[0] + 1,
                        "start_byte": node.start_byte,
                        "end_byte": node.end_byte,
                    })

            # Class declarations: class Foo {}
            elif node.type == "class_declaration":
                name_node = node.child_by_field_name("name")
                result["classes"].append({
                    "name": _get_text(name_node, code) if name_node else "<anon>",
                    "start_line": node.start_point[0] + 1,
                    "end_line": node.end_point[0] + 1,
                })

            # Imports: import { x } from "./module"
            elif node.type in self.import_node_types:
                result["imports"].append(_get_text(node, code))

            # Exports: export const x = ... / export default function() {}
            elif node.type == "export_statement":
                result["imports"].append(_get_text(node, code))

            # Function calls: foo() or obj.foo()
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
            if node.type in ("function_declaration", "method_definition"):
                name_node = node.child_by_field_name("name")
                if name_node and _get_text(name_node, code) == symbol_name:
                    return node
            # Arrow functions: const foo = () => {}
            if node.type == "arrow_function":
                parent = node.parent
                if parent and parent.type == "variable_declarator":
                    name_node = parent.child_by_field_name("name")
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

        # Extract name and params based on node type
        if func_node.type == "function_declaration":
            name_node = func_node.child_by_field_name("name")
            params_node = func_node.child_by_field_name("parameters")
        elif func_node.type == "method_definition":
            name_node = func_node.child_by_field_name("name")
            params_node = func_node.child_by_field_name("parameters")
        else:  # arrow_function
            parent = func_node.parent
            name_node = parent.child_by_field_name("name") if parent else None
            params_node = func_node.child_by_field_name("parameters")

        name = _get_text(name_node, code) if name_node else symbol_name

        params = []
        if params_node:
            for child in params_node.children:
                if child.type in ("identifier", "required_parameter", "optional_parameter"):
                    pname_node = child.child_by_field_name("name") or child
                    params.append({
                        "name": _get_text(pname_node, code),
                        "type": None,  # JS динамическая типизация
                    })

        return {
            "name": name,
            "params": params,
            "return_type": None,
            "docstring": None,
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

            elif node.type == "method_definition":
                name_node = node.child_by_field_name("name")
                current_function = _get_text(name_node, code) if name_node else None
                if current_function:
                    graph[current_function] = []

            elif node.type == "arrow_function":
                parent = node.parent
                if parent and parent.type == "variable_declarator":
                    name_node = parent.child_by_field_name("name")
                    current_function = _get_text(name_node, code) if name_node else None
                    if current_function and current_function not in graph:
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
register("javascript", JavaScriptAnalyzer)