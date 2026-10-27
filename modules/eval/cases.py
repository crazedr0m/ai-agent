# -*- coding: utf-8 -*-
# modules/eval/cases.py — Golden-кейсы для eval-харнесса

from dataclasses import dataclass
from typing import Optional


@dataclass
class EvalCase:
    """Один golden-кейс: задача → ожидаемый вызов инструмента."""
    id: str
    system_prompt: str
    task: str
    expected_tool: Optional[str]      # None = не должно быть вызова
    expected_args: Optional[str] = None  # None = любой аргумент
    description: str = ""


# System prompt для eval — минимальный, сообщающий о доступных инструментах
EVAL_SYSTEM = """Ты — полезный ассистент с доступом к инструментам.

Инструменты:
- list_dir(path): показать содержимое папки
- view_file_outline(file_path): показать сигнатуры функций и классов в файле
- read_file_chunk(file_path, start_line, end_line): прочитать диапазон строк из файла
- query_db_schema(db_path): показать структуру таблиц SQLite БД

Чтобы вызвать инструмент, используй строго этот формат:
<call name="имя_инструмента">аргументы</call>

После получения результата проанализируй его и дай ответ пользователю.
Если инструмент не нужен — просто ответь текстом."""

EVAL_CASES = [
    EvalCase(
        id="list_dir_dot",
        system_prompt=EVAL_SYSTEM,
        task="Покажи содержимое текущей папки.",
        expected_tool="list_dir",
        expected_args=None,
        description="list_dir с точкой",
    ),
    EvalCase(
        id="read_file_chunk",
        system_prompt=EVAL_SYSTEM,
        task="Прочитай строки 10-20 из файла test_core.py.",
        expected_tool="read_file_chunk",
        expected_args=None,
        description="read_file_chunk с диапазоном",
    ),
    EvalCase(
        id="no_tool_needed",
        system_prompt=EVAL_SYSTEM,
        task="Какой сегодня день недели? Ответь просто текстом.",
        expected_tool=None,
        expected_args=None,
        description="нет вызова — только текст",
    ),
    EvalCase(
        id="view_file_outline",
        system_prompt=EVAL_SYSTEM,
        task="Покажи структуру файла core/core.py.",
        expected_tool="view_file_outline",
        expected_args=None,
        description="view_file_outline с именем файла",
    ),
    EvalCase(
        id="list_dir_nested",
        system_prompt=EVAL_SYSTEM,
        task="Что находится в папке agents?",
        expected_tool="list_dir",
        expected_args=None,
        description="list_dir с вложенной папкой",
    ),
    EvalCase(
        id="read_with_special_chars",
        system_prompt=EVAL_SYSTEM,
        task="Прочитай строки 1-5 из файла README_TUI.md.",
        expected_tool="read_file_chunk",
        expected_args=None,
        description="read_file_chunk с подчёркиванием в имени",
    ),
    EvalCase(
        id="query_db",
        system_prompt=EVAL_SYSTEM,
        task="Покажи схему базы данных из файла data.db.",
        expected_tool="query_db_schema",
        expected_args=None,
        description="query_db_schema с путём к БД",
    ),
]