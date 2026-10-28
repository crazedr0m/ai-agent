# -*- coding: utf-8 -*-
# tests/test_parser.py — Тесты для modules/parser.py

import unittest
import re

from tests import *  # noqa: sys.path


class TestExtractCodeFromMarkdown(unittest.TestCase):
    """Тесты для extract_code_from_markdown()."""

    def test_empty_string(self):
        from modules.parser import extract_code_from_markdown
        self.assertEqual(extract_code_from_markdown(""), "")

    def test_none_string(self):
        from modules.parser import extract_code_from_markdown
        self.assertEqual(extract_code_from_markdown(None), "")

    def test_python_block(self):
        from modules.parser import extract_code_from_markdown
        result = extract_code_from_markdown(
            "```python\nprint('hello')\n```"
        )
        self.assertEqual(result, "print('hello')")

    def test_json_block(self):
        from modules.parser import extract_code_from_markdown
        result = extract_code_from_markdown(
            '```json\n{"key": "value"}\n```'
        )
        self.assertEqual(result, '{"key": "value"}')

    def test_block_without_language(self):
        from modules.parser import extract_code_from_markdown
        result = extract_code_from_markdown(
            "```\nplain code block\n```"
        )
        self.assertEqual(result, "plain code block")

    def test_javascript_block(self):
        from modules.parser import extract_code_from_markdown
        result = extract_code_from_markdown(
            "```javascript\nconst x = 1;\n```"
        )
        self.assertEqual(result, "const x = 1;")

    def test_multiline_block(self):
        from modules.parser import extract_code_from_markdown
        result = extract_code_from_markdown(
            "```python\ndef foo():\n    return 42\n```"
        )
        self.assertEqual(result, "def foo():\n    return 42")

    def test_first_block_extracted(self):
        from modules.parser import extract_code_from_markdown
        result = extract_code_from_markdown(
            "```python\nfirst\n```\ntext\n```python\nsecond\n```"
        )
        self.assertEqual(result, "first")

    def test_json_fallback_no_fence(self):
        from modules.parser import extract_code_from_markdown
        result = extract_code_from_markdown(
            'Some text {"key": "value"} more text'
        )
        self.assertEqual(result, '{"key": "value"}')

    def test_json_fallback_nested(self):
        from modules.parser import extract_code_from_markdown
        result = extract_code_from_markdown(
            '{"outer": {"inner": [1, 2, 3]}}'
        )
        self.assertEqual(result, '{"outer": {"inner": [1, 2, 3]}}')

    def test_no_match_returns_empty(self):
        from modules.parser import extract_code_from_markdown
        self.assertEqual(
            extract_code_from_markdown("Просто текст без кода"), ""
        )

    def test_only_whitespace(self):
        from modules.parser import extract_code_from_markdown
        self.assertEqual(extract_code_from_markdown("   \n  "), "")


class TestHasJsonBlock(unittest.TestCase):
    """Тесты для has_json_block()."""

    def test_has_json_block_positive(self):
        from modules.parser import has_json_block
        self.assertTrue(
            has_json_block('```json\n{"key": "value"}\n```')
        )

    def test_has_json_block_inline_brace(self):
        from modules.parser import has_json_block
        self.assertTrue(
            has_json_block('```json{"key": "value"}```')
        )

    def test_python_block_is_not_json(self):
        from modules.parser import has_json_block
        self.assertFalse(
            has_json_block("```python\nprint('hi')\n```")
        )

    def test_empty_string_false(self):
        from modules.parser import has_json_block
        self.assertFalse(has_json_block(""))

    def test_plain_text_false(self):
        from modules.parser import has_json_block
        self.assertFalse(has_json_block("no code here"))

    def test_case_insensitive_json(self):
        from modules.parser import has_json_block
        self.assertTrue(
            has_json_block('```JSON\n{"key": 1}\n```')
        )


if __name__ == "__main__":
    unittest.main()