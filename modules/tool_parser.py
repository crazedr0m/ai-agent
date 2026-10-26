# -*- coding: utf-8 -*-
# modules/tool_parser.py — Мультиформатный парсер вызовов инструментов
#
# Фаза 1.4: три стратегии получения вызова + толерантный парсинг.
#
# parse_tool_call(text) -> Optional[tuple[str, str]]
#   Возвращает (tool_name, raw_args) или None если вызов не найден.

import json
import re
from typing import Optional


# ──────────────────────────────────────────────
# Толерантный XML-парсер
# ──────────────────────────────────────────────

_RE_XML_CALL = re.compile(
    r'<call\s+name="(\w+)"\s*>(.*?)</call>',
    re.DOTALL,
)

# Альтернативные XML-вариации: <tool_call>, <function_call>, <invoke>
_RE_ALT_XML = re.compile(
    r'<tool_call>\s*<tool_name>(\w+)</tool_name>\s*<parameters>(.*?)</parameters>\s*</tool_call>',
    re.DOTALL,
)


def _parse_xml(text: str) -> Optional[tuple[str, str]]:
    """Стандартный XML-формат: <call name="x">args</call>."""
    m = _RE_XML_CALL.search(text)
    if m:
        return m.group(1), m.group(2).strip()
    return None


def _parse_hermes_xml(text: str) -> Optional[tuple[str, str]]:
    """Hermes-формат: <tool_call><tool_name>x</tool_name><parameters>...</parameters></tool_call>."""
    m = _RE_ALT_XML.search(text)
    if m:
        return m.group(1), m.group(2).strip()
    return None


# ──────────────────────────────────────────────
# JSON в ```-блоке или голый JSON-объект
# ──────────────────────────────────────────────

_RE_JSON_BLOCK = re.compile(
    r'```(?:json)?\s*\n?(\{.*?\})\n?\s*```',
    re.DOTALL,
)

_RE_PLAIN_JSON_CALL = re.compile(
    r'\{\s*"name"\s*:\s*"(\w+)"\s*,\s*"arguments"\s*:\s*(\{.*?\})\s*\}',
    re.DOTALL,
)


def _parse_json_block(text: str) -> Optional[tuple[str, str]]:
    """JSON в markdown-блоке: ```json {"name": "x", "arguments": {...}} ```."""
    m = _RE_JSON_BLOCK.search(text)
    if m:
        try:
            data = json.loads(m.group(1))
            name = data.get("name")
            args = data.get("arguments") or data.get("parameters") or {}
            if name:
                return name, json.dumps(args) if isinstance(args, dict) else str(args)
        except (json.JSONDecodeError, ValueError):
            pass
    return None


def _parse_plain_json(text: str) -> Optional[tuple[str, str]]:
    """Голый JSON-объект: {"name": "x", "arguments": {...}}."""
    m = _RE_PLAIN_JSON_CALL.search(text)
    if m:
        name = m.group(1)
        raw = m.group(2)
        return name, raw
    return None


# ──────────────────────────────────────────────
# Срезание думательного префикса (reasoning models)
# ──────────────────────────────────────────────

_THINK_PATTERN = re.compile(r'^.*?</think>', re.DOTALL)


def _strip_thinking(text: str) -> str:
    """Срезать префикс </think> и другие мыслительные блоки."""
    # deepseek-r1 формат:  ... response
    text = _THINK_PATTERN.sub('', text, count=1).strip()

    # Альтернативный формат:  ...
    if ' response>' in text:
        text = text.split(' response>')[-1].strip()

    return text


# ──────────────────────────────────────────────
# Единая точка входа
# ──────────────────────────────────────────────

_STRATEGIES = [
    ("xml", _parse_xml),
    ("hermes_xml", _parse_hermes_xml),
    ("json_block", _parse_json_block),
    ("plain_json", _parse_plain_json),
]


def parse_tool_call(text: str) -> Optional[tuple[str, str]]:
    """Попробовать все стратегии парсинга вызова инструмента.

    Сначала пробует на оригинальном тексте, затем — после срезания
    мыслительного блока (для reasoning-моделей).

    Возвращает (tool_name, raw_args) или None.
    """
    if not text:
        return None

    # 1. Пробуем на оригинальном тексте
    for name, strategy in _STRATEGIES:
        result = strategy(text)
        if result is not None:
            return result

    # 2. Пробуем после срезания think-блока
    cleaned = _strip_thinking(text)
    if cleaned != text:
        for name, strategy in _STRATEGIES:
            result = strategy(cleaned)
            if result is not None:
                return result

    return None