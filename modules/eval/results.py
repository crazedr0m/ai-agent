# -*- coding: utf-8 -*-
# modules/eval/results.py — Типы результатов eval-прогонов

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EvalResult:
    """Результат прогона одного кейса на одной модели."""
    case_id: str
    model: str
    raw_response: str                    # сырой ответ LLM
    parsed_tool: Optional[str]           # что распарсил execute_tool_call
    parsed_args: Optional[str]
    expected_tool: Optional[str]
    expected_args: Optional[str]         # None = проверяем только имя
    tool_correct: bool = False           # совпало имя инструмента
    args_correct: bool = False           # аргументы (если expected_args задан)
    overall_pass: bool = False           # полное совпадение
    error: Optional[str] = None          # ошибка выполнения
    duration_ms: int = 0


@dataclass
class ModelReport:
    """Сводка по одной модели."""
    model: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    tool_accuracy: float = 0.0
    avg_duration_ms: float = 0.0
    results: list = field(default_factory=list)