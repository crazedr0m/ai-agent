# -*- coding: utf-8 -*-
# core_tools.py — Инструменты для агентов
#
# Все инструменты зарегистрированы через @register_tool из core.core_tools.
# Старая TOOLS_MAP удалена — реестр теперь в _GLOBAL_REGISTRY.

import os
import sqlite3

from core.core_tools import register_tool


@register_tool("list_dir", "Показать содержимое папки")
def list_dir(path: str) -> str:
    """Аналог ls: возвращает список файлов в папке."""
    try:
        return "\n".join(os.listdir(path))
    except Exception as e:
        return f"Ошибка чтения папки: {e}"


@register_tool("view_file_outline", "Показать сигнатуры функций и классов в файле")
def view_file_outline(file_path: str) -> str:
    """Сканирует файл и вытаскивает ТОЛЬКО сигнатуры функций и классов."""
    try:
        outline = []
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f, 1):
                stripped = line.strip()
                if stripped.startswith(("def ", "class ", "async def ")):
                    outline.append(f"Строка {i}: {stripped}")
        return "\n".join(outline) if outline else "Функции и классы не найдены."
    except Exception as e:
        return f"Ошибка анализа структуры файла: {e}"


@register_tool("read_file_chunk", "Прочитать диапазон строк из файла")
def read_file_chunk(file_path: str, start_line: int = 1, end_line: int = 50) -> str:
    """Аналог cat с лимитом: читает строго определенный диапазон строк."""
    try:
        lines_to_return = []
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f, 1):
                if start_line <= i <= end_line:
                    lines_to_return.append(f"{i}: {line.rstrip()}")
                if i > end_line:
                    break
        return "\n".join(lines_to_return)
    except Exception as e:
        return f"Ошибка чтения файла: {e}"


@register_tool("query_db_schema", "Показать структуру таблиц SQLite БД")
def query_db_schema(db_path: str) -> str:
    """Показывает структуру таблиц в базе данных (SQLite)."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        conn.close()
        return "\n\n".join([f"Таблица: {name}\nСхема: {sql}" for name, sql in tables])
    except Exception as e:
        return f"Ошибка чтения схемы БД: {e}"
