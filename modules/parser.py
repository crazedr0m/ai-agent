# -*- coding: utf-8 -*-
import re


def extract_code_from_markdown(text: str) -> str:
    """Извлекает код из markdown-блока ```lang независимо от языка.
    Поддерживает: ```python, ```json, ```javascript, ``` или просто ``` без языка.
    Если блок не найден, пытается извлечь JSON-объект из текста напрямую.
    """
    if not text:
        return ""

    # 1) Ищем ЛЮБОЙ ```...``` блок (с опциональным language hint)
    match = re.search(r"```\w*\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # 2) Fallback: ищем JSON-подобную структуру в тексте (если модель забыла завернуть в ```)
    json_match = re.search(r'\{\s*"[^"]+".*\}', text, re.DOTALL)
    if json_match:
        return json_match.group(0).strip()

    return ""


def has_json_block(text: str) -> bool:
    """Проверяет, содержит ли текст ```json блок."""
    return bool(re.search(r"```json\s*\{", text, re.DOTALL | re.IGNORECASE))