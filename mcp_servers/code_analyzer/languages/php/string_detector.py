# -*- coding: utf-8 -*-
# mcp_servers/code_analyzer/languages/php/string_detector.py — Детекция HTML/JS/CSS в строковых литералах PHP
#
# Анализирует PHP-строки на предмет вложенных языков:
#   - HTML-фрагменты (<tag>, </tag>, <!DOCTYPE)
#   - JavaScript-фрагменты (<script>, onEvent=, window., document.)
#   - CSS-фрагменты (<style>, style=)
#   - JSON-фрагменты (в json_encode(), return {...})
#
# Используется PhpAnalyzer'ом и PHP→JS bridge'ом (cross_language/php_js_bridge.py).

import re
from typing import Protocol


# ── Регулярные выражения для детекции ──────────────────────────────

# Триггеры HTML-фрагментов
_RE_HTML_TRIGGER = re.compile(
    r"<(!DOCTYPE\s+html|html[\s>]|head[\s>]|body[\s>]|script[\s>]|style[\s>]|"
    r"div[\s>]|span[\s>]|a[\s>]|form[\s>]|input[\s>]|select[\s>]|table[\s>]|"
    r"/html>|/body>|/head>|br\s*/?>|<[a-z]+\s)",
    re.IGNORECASE,
)

# Триггеры inline JavaScript
_RE_JS_INLINE = re.compile(
    r"\b(onclick|onload|onchange|onsubmit|onmouseover|onerror|onfocus|onblur)"
    r"\s*=",
    re.IGNORECASE,
)

# Триггеры JS-кода (не обязательно внутри <script>)
_RE_JS_CODE = re.compile(
    r"\b(alert|console\.|document\.|window\.|function\s+\w+\s*\(|"
    r"var\s+\w+|let\s+\w+|const\s+\w+|"
    r"\$\s*\(\s*['\"`]|\.addEventListener|\.getElementById)\b",
)

# Извлечение содержимого <script> тегов
_RE_SCRIPT = re.compile(
    r"<script[^>]*>(.*?)</script>",
    re.DOTALL | re.IGNORECASE,
)

# Триггеры JSON
_RE_JSON_LIKE = re.compile(
    r"^\s*\{[^}]*\}s*$|^\s*\[.*\]s*$",
)


# ── Результат ────────────────────────────────────────────────────


class StringFragment:
    """Фрагмент строкового литерала PHP."""

    kind: str  # "html" | "js" | "css" | "json" | "unknown"
    content: str
    start_byte: int
    end_byte: int
    inner_language: str | None  # "html" | "javascript" | "css" | "json"


    def __init__(self, kind, content, start_byte, end_byte, inner_language=None):
        self.kind = kind
        self.content = content
        self.start_byte = start_byte
        self.end_byte = end_byte
        self.inner_language = inner_language

    def __repr__(self):
        return (f"StringFragment(kind={self.kind!r}, "
                f"content={self.content[:50]!r}..., "
                f"inner_language={self.inner_language!r})")


# ── Основная функция ─────────────────────────────────────────────


def detect_string_content(content: str, start_byte: int = 0) -> list[StringFragment]:
    """Проанализировать содержимое строкового литерала на вложенные языки.

    Args:
        content: текст строки (без кавычек)
        start_byte: смещение начала в файле (для AST-ссылок)

    Returns:
        список StringFragment с обнаруженными фрагментами
    """
    fragments: list[StringFragment] = []

    # Проверка на JSON-подобные строки
    if _RE_JSON_LIKE.search(content):
        fragments.append(StringFragment(
            kind="json",
            content=content,
            start_byte=start_byte,
            end_byte=start_byte + len(content),
            inner_language="json",
        ))
        return fragments

    # Проверка на HTML (содержит <tag>)
    if _RE_HTML_TRIGGER.search(content):
        # Ищем <script>-блоки
        for match in _RE_SCRIPT.finditer(content):
            js_start = start_byte + match.start(1)
            js_end = start_byte + match.end(1)
            fragments.append(StringFragment(
                kind="js",
                content=match.group(1).strip(),
                start_byte=js_start,
                end_byte=js_end,
                inner_language="javascript",
            ))

        # Ищем inline-JS (onclick, onload и т.д.)
        for match in _RE_JS_INLINE.finditer(content):
            # Берём весь атрибут до кавычки
            attr_end = content.find('"', match.end())
            if attr_end == -1:
                attr_end = content.find("'", match.end())
                if attr_end == -1:
                    attr_end = match.end() + 50
                else:
                    # Нашли закрывающую кавычку
                    pass

            inline_start = start_byte + match.start()
            inline_end = start_byte + min(attr_end + 1, len(content))
            js_content = content[match.start():attr_end + 1] if attr_end > 0 else ""
            fragments.append(StringFragment(
                kind="js",
                content=js_content,
                start_byte=inline_start,
                end_byte=inline_end,
                inner_language="javascript",
            ))

        # Сам HTML-фрагмент
        fragments.append(StringFragment(
            kind="html",
            content=content,
            start_byte=start_byte,
            end_byte=start_byte + len(content),
            inner_language="html",
        ))

        return fragments

    # Проверка на JS-код (без HTML-обёртки)
    if _RE_JS_CODE.search(content):
        fragments.append(StringFragment(
            kind="js",
            content=content,
            start_byte=start_byte,
            end_byte=start_byte + len(content),
            inner_language="javascript",
        ))
        return fragments

    return fragments


def extract_js_from_php_file(filepath: str) -> list[StringFragment]:
    """Извлечь все JS-фрагменты из PHP-файла.

    Используется PHP→JS bridge'ом.

    Args:
        filepath: путь к PHP-файлу

    Returns:
        список JS-фрагментов, найденных в строковых литералах
    """
    # Испортируем здесь, чтобы избежать циклических импортов
    from mcp_servers.code_analyzer.core import _parse_file
    import tree_sitter_php
    from tree_sitter import Language, Parser

    lang = Language(tree_sitter_php.language_php())
    parser = Parser(lang)

    parsed = _parse_file(filepath, parser)
    if parsed is None:
        return []

    root = parsed["root"]
    code = parsed["code"]
    results: list[StringFragment] = []

    def walk(node):
        # Ищем строковые литералы: encapsed_string, string_literal, heredoc
        if node.type == "encapsed_string":
            raw = code[node.start_byte:node.end_byte]
            inner = raw[1:-1]  # снимаем кавычки
            detected = detect_string_content(inner, node.start_byte + 1)
            results.extend(d for d in detected if d.kind in ("js", "html"))

        elif node.type in ("string_literal", "heredoc"):
            inner = _get_text(node, code)
            detected = detect_string_content(inner, node.start_byte)
            results.extend(d for d in detected if d.kind in ("js", "html"))

        # Ищем echo/print с строковыми аргументами
        elif node.type == "echo_statement":
            for child in node.children:
                walk(child)
            return  # дети уже обошли, не идём дальше

        for child in node.children:
            walk(child)

    # Нужен _get_text из core
    from mcp_servers.code_analyzer.core import _get_text  # noqa

    walk(root)
    return results