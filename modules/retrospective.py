# -*- coding: utf-8 -*-
# modules/retrospective.py — Ретроспектива по трейсам (Фаза 4.4)
#
# Анализирует JSONL-трейсы, находит повторяющиеся ошибки
# и формулирует предложения по улучшению.
#
# Использование:
#     from modules.retrospective import Retrospective
#     retro = Retrospective()
#     report = retro.analyze()
#     print(report.summary)

import json
import os
import glob
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Optional


class Retrospective:
    """Анализ трейсов для поиска повторяющихся ошибок.

    Читает все JSONL-файлы из traces/session_* и собирает:
    - Типы ошибок (по содержимому tool_result с ошибками)
    - Инструменты, которые чаще всего падают
    - Модели, которые чаще всего ошибаются
    - Повторяющиеся паттерны в ошибках
    """

    def __init__(self, traces_dir: str = "traces",
                 min_occurrences: int = 2):
        """
        Args:
            traces_dir: директория с трейсами
            min_occurrences: минимальное число повторений для включения в отчёт
        """
        self.traces_dir = traces_dir
        self.min_occurrences = min_occurrences
        self._sessions = []
        self._errors = []
        self._tool_calls = []
        self._llm_calls = []

    # ─────────────────────────────────────────────
    # Публичные методы
    # ─────────────────────────────────────────────

    def analyze(self) -> "RetroReport":
        """Запустить анализ трейсов."""
        self._load_sessions()
        # Классификация ошибок происходит в _load_jsonl → _classify_tool_result

        report = RetroReport(
            total_sessions=len(self._sessions),
            total_errors=len(self._errors),
            total_tool_calls=len(self._tool_calls),
        )

        # Повторяющиеся ошибки
        error_patterns = self._find_error_patterns()
        for pattern, count in error_patterns:
            if count >= self.min_occurrences:
                report.add_finding(
                    type="recurring_error",
                    description=pattern,
                    count=count,
                    suggestion=self._suggest_fix(pattern),
                )

        # Инструменты с наибольшим числом ошибок
        tool_failures = self._tool_failure_rates()
        for tool_name, fail_count, total_count in tool_failures[:5]:
            if fail_count >= self.min_occurrences:
                rate = (fail_count / total_count * 100) if total_count > 0 else 0
                report.add_finding(
                    type="tool_failure",
                    description=f"Инструмент '{tool_name}' упал {fail_count}/{total_count} раз ({rate:.0f}%)",
                    count=fail_count,
                    suggestion=self._suggest_tool_fix(tool_name, fail_count),
                )

        # Модели с наибольшим числом ошибок
        model_failures = self._model_failure_rates()
        for model, fail_count, total_count in model_failures[:3]:
            if fail_count >= self.min_occurrences:
                rate = (fail_count / total_count * 100) if total_count > 0 else 0
                report.add_finding(
                    type="model_failure",
                    description=f"Модель '{model}' ошиблась {fail_count}/{total_count} раз ({rate:.0f}%)",
                    count=fail_count,
                    suggestion="Проверить профиль модели в model_profiles.json: "
                               "возможно, нужна другая температура или num_ctx",
                )

        return report

    # ─────────────────────────────────────────────
    # Загрузка данных
    # ─────────────────────────────────────────────

    def _load_sessions(self):
        """Загрузить все JSONL-файлы из traces/session_*/trace.jsonl."""
        pattern = os.path.join(self.traces_dir, "session_*", "trace.jsonl")
        for jsonl_path in sorted(glob.glob(pattern)):
            session_id = os.path.basename(os.path.dirname(jsonl_path))
            self._load_jsonl(session_id, jsonl_path)

    def _load_jsonl(self, session_id: str, path: str):
        """Загрузить один JSONL-файл."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    step_type = record.get("type", "")
                    if step_type == "tool_call":
                        self._tool_calls.append(record)
                    elif step_type == "tool_result":
                        self._classify_tool_result(record)
                    elif step_type == "llm_call":
                        self._llm_calls.append(record)
                    elif step_type == "__session_start__":
                        self._sessions.append(record)
        except (IOError, json.JSONDecodeError):
            pass

    def _classify_tool_result(self, record: dict):
        """Классифицировать результат инструмента как ошибку или успех."""
        content = record.get("content", "")
        metadata = record.get("metadata", {})

        # Признаки ошибки
        is_error = False
        error_type = "unknown"

        if content.startswith("Ошибка") or content.startswith("Error"):
            is_error = True
            error_type = "execution_error"
        elif "не найден" in content or "not found" in content.lower():
            is_error = True
            error_type = "not_found"
        elif "не зарегистрирован" in content:
            is_error = True
            error_type = "unknown_tool"
        elif "validation" in content.lower() and "error" in content.lower():
            is_error = True
            error_type = "validation_error"
        elif "Missing required" in content:
            is_error = True
            error_type = "missing_argument"

        if is_error:
            self._errors.append({
                "content": content[:500],
                "tool_name": metadata.get("tool_name", "?"),
                "error_type": error_type,
                "session_id": record.get("session_id", "?"),
            })

    # ─────────────────────────────────────────────
    # Анализ
    # ─────────────────────────────────────────────

    def _find_error_patterns(self) -> list[tuple[str, int]]:
        """Найти повторяющиеся паттерны в ошибках."""
        # Группируем по error_type + tool_name
        pattern_counts = Counter()
        for err in self._errors:
            key = f"[{err['error_type']}] {err['tool_name']}: {err['content'][:100]}"
            pattern_counts[key] += 1

        # Сортируем по частоте
        return pattern_counts.most_common(20)

    def _tool_failure_rates(self) -> list[tuple[str, int, int]]:
        """Статистика отказов по инструментам."""
        tool_total = Counter()
        tool_fails = Counter()

        for call in self._tool_calls:
            name = call.get("metadata", {}).get("tool_name", "?")
            tool_total[name] += 1

        for err in self._errors:
            name = err["tool_name"]
            tool_fails[name] += 1

        # Сортируем по числу отказов
        result = []
        for name in tool_fails:
            result.append((name, tool_fails[name], tool_total.get(name, 0)))
        result.sort(key=lambda x: -x[1])
        return result

    def _model_failure_rates(self) -> list[tuple[str, int, int]]:
        """Статистика отказов по моделям."""
        model_total = Counter()
        model_fails = Counter()

        for call in self._llm_calls:
            model = call.get("metadata", {}).get("model", "?")
            model_total[model] += 1

        # Считаем ошибки после LLM-вызовов (грубо: ошибка в той же сессии)
        for err in self._errors:
            # Ищем модель по сессии
            model = self._find_model_for_session(err["session_id"])
            if model:
                model_fails[model] += 1

        result = []
        for model in model_fails:
            result.append((model, model_fails[model], model_total.get(model, 0)))
        result.sort(key=lambda x: -x[1])
        return result

    def _find_model_for_session(self, session_id: str) -> Optional[str]:
        """Найти модель, использованную в сессии."""
        for call in self._llm_calls:
            if call.get("session_id") == session_id:
                model = call.get("metadata", {}).get("model", "")
                if model:
                    return model
        return None

    def _suggest_fix(self, pattern: str) -> str:
        """Сгенерировать предложение по исправлению на основе паттерна ошибки."""
        if "validation_error" in pattern:
            return "Проверить JSON Schema инструмента — возможно, не хватает обязательных полей"
        if "missing_argument" in pattern:
            return "Добавить значения по умолчанию для опциональных аргументов в схеме инструмента"
        if "unknown_tool" in pattern:
            return "Проверить регистрацию инструмента — возможно, имя не совпадает"
        if "not_found" in pattern:
            return "Добавить более информативное сообщение об ошибке с путём"
        if "execution_error" in pattern:
            return "Добавить try/except в реализацию инструмента"
        return "Проанализировать трейс и исправить корневую причину"

    def _suggest_tool_fix(self, tool_name: str, fail_count: int) -> str:
        """Сгенерировать предложение для конкретного инструмента."""
        return (f"Инструмент '{tool_name}' упал {fail_count} раз. "
                f"Проверить обработку граничных случаев и добавить защиту от некорректных аргументов.")


class RetroReport:
    """Отчёт ретроспективы."""

    def __init__(self, total_sessions: int, total_errors: int,
                 total_tool_calls: int):
        self.total_sessions = total_sessions
        self.total_errors = total_errors
        self.total_tool_calls = total_tool_calls
        self.findings = []

    def add_finding(self, type: str, description: str,
                    count: int, suggestion: str):
        self.findings.append({
            "type": type,
            "description": description,
            "count": count,
            "suggestion": suggestion,
        })

    @property
    def summary(self) -> str:
        """Краткая сводка."""
        lines = [
            f"📊 Ретроспектива трейсов",
            f"{'='*50}",
            f"Сессий: {self.total_sessions}",
            f"Вызовов инструментов: {self.total_tool_calls}",
            f"Ошибок: {self.total_errors}",
            f"Найдено проблем: {len(self.findings)}",
            "",
        ]

        if not self.findings:
            lines.append("✅ Проблем не найдено.")
            return "\n".join(lines)

        for i, f in enumerate(self.findings, 1):
            lines.append(f"\n{i}. [{f['type']}] {f['description']}")
            lines.append(f"   Повторений: {f['count']}")
            lines.append(f"   💡 {f['suggestion']}")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "total_sessions": self.total_sessions,
            "total_errors": self.total_errors,
            "total_tool_calls": self.total_tool_calls,
            "findings": self.findings,
        }

    def save(self, path: str = None):
        """Сохранить отчёт в JSON."""
        if path is None:
            os.makedirs("traces/retro", exist_ok=True)
            path = f"traces/retro/retro_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)