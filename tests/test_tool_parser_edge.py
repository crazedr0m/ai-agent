# -*- coding: utf-8 -*-
# tests/test_tool_parser_edge.py — Тесты для modules/tool_parser.py
# Покрывает: все стратегии парсинга, think-блоки, edge cases

import unittest
import json

from tests import *  # noqa: sys.path


class TestParseXml(unittest.TestCase):
    """Тесты для _parse_xml()."""

    def test_simple_xml_call(self):
        from modules.tool_parser import _parse_xml
        result = _parse_xml('<call name="read_file">path: "."</call>')
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "read_file")
        self.assertEqual(result[1], 'path: "."')

    def test_xml_with_newlines(self):
        from modules.tool_parser import _parse_xml
        result = _parse_xml('<call name="write_file">\ncontent: "hello"\n</call>')
        self.assertEqual(result[0], "write_file")
        self.assertEqual(result[1], 'content: "hello"')

    def test_xml_no_match(self):
        from modules.tool_parser import _parse_xml
        self.assertIsNone(_parse_xml("just some text"))

    def test_xml_empty_name(self):
        from modules.tool_parser import _parse_xml
        self.assertIsNone(_parse_xml('<call name="">args</call>'))


class TestParseHermesXml(unittest.TestCase):
    """Тесты для _parse_hermes_xml()."""

    def test_hermes_xml_simple(self):
        from modules.tool_parser import _parse_hermes_xml
        text = ("<tool_call><tool_name>search_code</tool_name>"
                "<parameters>pattern: test</parameters></tool_call>")
        result = _parse_hermes_xml(text)
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "search_code")
        self.assertEqual(result[1], "pattern: test")

    def test_hermes_xml_multiline(self):
        from modules.tool_parser import _parse_hermes_xml
        text = ("<tool_call>\n<tool_name>run_command</tool_name>\n"
                "<parameters>\ncmd: ls\n</parameters>\n</tool_call>")
        result = _parse_hermes_xml(text)
        self.assertEqual(result[0], "run_command")

    def test_hermes_xml_no_match(self):
        from modules.tool_parser import _parse_hermes_xml
        self.assertIsNone(_parse_hermes_xml("<call name='x'>args</call>"))


class TestParseJsonBlock(unittest.TestCase):
    """Тесты для _parse_json_block()."""

    def test_json_block_with_name_and_arguments(self):
        from modules.tool_parser import _parse_json_block
        text = '```json\n{"name": "my_tool", "arguments": {"key": "val"}}\n```'
        result = _parse_json_block(text)
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "my_tool")
        self.assertIn("key", result[1])

    def test_json_block_with_parameters_field(self):
        from modules.tool_parser import _parse_json_block
        text = '```\n{"name": "tool_x", "parameters": {"a": 1}}\n```'
        result = _parse_json_block(text)
        self.assertEqual(result[0], "tool_x")
        self.assertIn("a", result[1])

    def test_json_block_invalid_json(self):
        from modules.tool_parser import _parse_json_block
        text = '```json\n{"name": "broken", "arguments": {invalid}\n```'
        result = _parse_json_block(text)
        self.assertIsNone(result)

    def test_json_block_no_name_field(self):
        from modules.tool_parser import _parse_json_block
        text = '```json\n{"not_name": "x", "arguments": {}}\n```'
        result = _parse_json_block(text)
        self.assertIsNone(result)

    def test_json_block_no_match(self):
        from modules.tool_parser import _parse_json_block
        self.assertIsNone(_parse_json_block("just text"))

    def test_json_block_arguments_as_string(self):
        from modules.tool_parser import _parse_json_block
        text = '```json\n{"name": "tool", "arguments": "raw string"}\n```'
        result = _parse_json_block(text)
        self.assertEqual(result[0], "tool")
        self.assertEqual(result[1], "raw string")


class TestParsePlainJson(unittest.TestCase):
    """Тесты для _parse_plain_json()."""

    def test_plain_json_simple(self):
        from modules.tool_parser import _parse_plain_json
        text = '{"name": "read_file", "arguments": {"path": "."}}'
        result = _parse_plain_json(text)
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "read_file")

    def test_plain_json_with_text_around(self):
        from modules.tool_parser import _parse_plain_json
        text = 'Some text {"name": "write_file", "arguments": {"c": "hello"}}'
        result = _parse_plain_json(text)
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "write_file")

    def test_plain_json_no_match(self):
        from modules.tool_parser import _parse_plain_json
        self.assertIsNone(_parse_plain_json('{"no": "name"}'))

    def test_plain_json_invalid(self):
        from modules.tool_parser import _parse_plain_json
        self.assertIsNone(_parse_plain_json("{broken}"))


class TestParseToolCall(unittest.TestCase):
    """Тесты для parse_tool_call() — единая точка входа."""

    def test_empty_text_returns_none(self):
        from modules.tool_parser import parse_tool_call
        self.assertIsNone(parse_tool_call(""))
        self.assertIsNone(parse_tool_call(None))

    def test_xml_strategy(self):
        from modules.tool_parser import parse_tool_call
        result = parse_tool_call('<call name="search_code">pattern: foo</call>')
        self.assertEqual(result[0], "search_code")

    def test_hermes_strategy(self):
        from modules.tool_parser import parse_tool_call
        text = ("<tool_call><tool_name>list_dir</tool_name>"
                "<parameters>path: .</parameters></tool_call>")
        result = parse_tool_call(text)
        self.assertEqual(result[0], "list_dir")

    def test_json_block_strategy(self):
        from modules.tool_parser import parse_tool_call
        text = '```json\n{"name": "read_file", "arguments": {"path": "."}}\n```'
        result = parse_tool_call(text)
        self.assertEqual(result[0], "read_file")

    def test_plain_json_strategy(self):
        from modules.tool_parser import parse_tool_call
        result = parse_tool_call('{"name": "my_tool", "arguments": {}}')
        self.assertEqual(result[0], "my_tool")

    def test_xml_after_think_block(self):
        """Вызов после think-блока с  response."""
        from modules.tool_parser import parse_tool_call
        text = "reasoning text response" + '<call name="read_file">path: .</call>'
        result = parse_tool_call(text)
        self.assertEqual(result[0], "read_file")

    def test_json_after_think_alternate(self):
        """Вызов после think-блока с  response>."""
        from modules.tool_parser import parse_tool_call
        text = ("prefix response>"
                '{"name": "json_tool", "arguments": {}}')
        result = parse_tool_call(text)
        self.assertEqual(result[0], "json_tool")

    def test_no_match_returns_none(self):
        from modules.tool_parser import parse_tool_call
        result = parse_tool_call("просто текст без вызова инструмента")
        self.assertIsNone(result)

    def test_priority_xml_over_json(self):
        """Парсер пробует XML в первую очередь."""
        from modules.tool_parser import parse_tool_call
        text = '<call name="xml_tool">arg</call> {"name": "json_tool", "arguments": {}}'
        result = parse_tool_call(text)
        self.assertEqual(result[0], "xml_tool")

    def test_first_call_returned(self):
        """Из нескольких вызовов возвращается первый."""
        from modules.tool_parser import parse_tool_call
        text = '<call name="first">a</call> <call name="second">b</call>'
        result = parse_tool_call(text)
        self.assertEqual(result[0], "first")


if __name__ == "__main__":
    unittest.main()