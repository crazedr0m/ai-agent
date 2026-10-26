# -*- coding: utf-8 -*-
# modules/eval_harness.py — Eval-харнесс для замера точности вызова инструментов
#
# Использует текущий ReActEngine.execute_tool_call() для парсинга.
# Замеряет долю корректных вызовов по golden-кейсам на каждой модели.
#
# Запуск:
#   python modules/eval_harness.py [модель1 модель2 ...]
#   python modules/eval_harness.py --all         # все доступные модели
#   python modules/eval_harness.py --quick       # только малые модели (быстрый прогон)

import json
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from typing import Optional

# Добавляем корень в path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core
from core.core import ReActEngine
from core.core_tools import _GLOBAL_REGISTRY


# ──────────────────────────────────────────────
# Golden-кейсы
# ──────────────────────────────────────────────

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
_EVAL_SYSTEM = """Ты — полезный ассистент с доступом к инструментам.

Инструменты:
- list_dir(path): показать содержимое папки
- view_file_outline(file_path): показать сигнатуры функций и классов в файле
- read_file_chunk(file_path, start_line, end_line): прочитать диапазон строк из файла
- query_db_schema(db_path): показать структуру таблиц SQLite БД

Чтобы вызвать инструмент, используй строго этот формат:
<call name="имя_инструмента">аргументы</call>

После получения результата проанализируй его и дай ответ пользователю.
Если инструмент не нужен — просто ответь текстом."""

_EVAL_CASES = [
    EvalCase(
        id="list_dir_dot",
        system_prompt=_EVAL_SYSTEM,
        task="Покажи содержимое текущей папки.",
        expected_tool="list_dir",
        expected_args=None,  # tool name — главное; аргументы документируем отдельно
        description="list_dir с точкой",
    ),
    EvalCase(
        id="read_file_chunk",
        system_prompt=_EVAL_SYSTEM,
        task="Прочитай строки 10-20 из файла test_core.py.",
        expected_tool="read_file_chunk",
        expected_args=None,
        description="read_file_chunk с диапазоном",
    ),
    EvalCase(
        id="no_tool_needed",
        system_prompt=_EVAL_SYSTEM,
        task="Какой сегодня день недели? Ответь просто текстом.",
        expected_tool=None,
        expected_args=None,
        description="нет вызова — только текст",
    ),
    EvalCase(
        id="view_file_outline",
        system_prompt=_EVAL_SYSTEM,
        task="Покажи структуру файла core/core.py.",
        expected_tool="view_file_outline",
        expected_args=None,
        description="view_file_outline с именем файла",
    ),
    EvalCase(
        id="list_dir_nested",
        system_prompt=_EVAL_SYSTEM,
        task="Что находится в папке agents?",
        expected_tool="list_dir",
        expected_args=None,  # tool name — главное
        description="list_dir с вложенной папкой",
    ),
    EvalCase(
        id="read_with_special_chars",
        system_prompt=_EVAL_SYSTEM,
        task="Прочитай строки 1-5 из файла README_TUI.md.",
        expected_tool="read_file_chunk",
        expected_args=None,
        description="read_file_chunk с подчёркиванием в имени",
    ),
    EvalCase(
        id="query_db",
        system_prompt=_EVAL_SYSTEM,
        task="Покажи схему базы данных из файла data.db.",
        expected_tool="query_db_schema",
        expected_args=None,
        description="query_db_schema с путём к БД",
    ),
]


# ──────────────────────────────────────────────
# Результаты
# ──────────────────────────────────────────────

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


# ──────────────────────────────────────────────
# Runner
# ──────────────────────────────────────────────

class EvalRunner:
    """Прогон golden-кейсов на моделях через текущий ReActEngine."""

    def __init__(self, models: list[str], cases: Optional[list[EvalCase]] = None,
                 timeout: int = 60, max_steps: int = 3):
        self.models = models
        self.cases = cases or _EVAL_CASES
        self.timeout = timeout
        self.max_steps = max_steps
        # Регистрируем инструменты
        import core_tools  # noqa

    def run_case(self, model: str, case: EvalCase) -> EvalResult:
        """Прогнать один кейс на одной модели.

        Вызывает LLM напрямую через call_ollama (не через ReActEngine.execute,
        чтобы получить сырой ответ и проверить execute_tool_call на нём).
        """
        start = time.time()

        try:
            # Формируем промпт как единый user-запрос (call_ollama использует
            # ChatML-шаблон: system + user + assistant)
            full_prompt = f"{case.system_prompt}\n\n{case.task}"
            raw = core.call_ollama(case.system_prompt, case.task,
                                   model_override=model)
            duration = int((time.time() - start) * 1000)

            if not raw:
                return EvalResult(
                    case_id=case.id, model=model,
                    raw_response="<пустой ответ>",
                    parsed_tool=None, parsed_args=None,
                    expected_tool=case.expected_tool,
                    expected_args=case.expected_args,
                    overall_pass=(case.expected_tool is None),
                    duration_ms=duration,
                )

            # Парсим сырой ответ через мультиформатный парсер (Фаза 1.4):
            # XML, Hermes XML, JSON-блок, plain JSON.
            from modules.tool_parser import parse_tool_call
            parsed = parse_tool_call(raw)
            if parsed is not None:
                parsed_tool, parsed_args = parsed
            else:
                parsed_tool = None
                parsed_args = None

            # Дополнительно прогоняем через execute_tool_call для лога
            engine = ReActEngine(max_steps=1, model=model)
            engine.execute_tool_call(raw)

            # Оценка
            if case.expected_tool is None:
                tool_correct = (parsed_tool is None)
                args_correct = True
            else:
                tool_correct = (parsed_tool == case.expected_tool)
                if case.expected_args is not None:
                    args_correct = (parsed_tool == case.expected_tool and
                                    parsed_args == case.expected_args)
                else:
                    args_correct = tool_correct

            overall_pass = tool_correct and args_correct

            return EvalResult(
                case_id=case.id, model=model,
                raw_response=raw[:500],
                parsed_tool=parsed_tool, parsed_args=parsed_args,
                expected_tool=case.expected_tool,
                expected_args=case.expected_args,
                tool_correct=tool_correct, args_correct=args_correct,
                overall_pass=overall_pass, duration_ms=duration,
            )

        except Exception as e:
            duration = int((time.time() - start) * 1000)
            return EvalResult(
                case_id=case.id, model=model,
                raw_response=f"<ОШИБКА: {e}>",
                parsed_tool=None, parsed_args=None,
                expected_tool=case.expected_tool,
                expected_args=case.expected_args,
                overall_pass=False, error=str(e), duration_ms=duration,
            )

    def run_all(self, progress: bool = True) -> list[ModelReport]:
        """Прогнать все кейсы на всех моделях."""
        reports = []
        for model in self.models:
            results = []
            for case in self.cases:
                if progress:
                    print(f"  [{model}] {case.id}...", end=" ", flush=True)
                result = self.run_case(model, case)
                results.append(result)
                if progress:
                    status = "✅" if result.overall_pass else "❌"
                    print(f"{status} ({result.duration_ms}ms)")
            report = self._build_report(model, results)
            reports.append(report)
        return reports

    def _build_report(self, model: str, results: list[EvalResult]) -> ModelReport:
        """Построить сводку по модели."""
        total = len(results)
        passed = sum(1 for r in results if r.overall_pass)
        failed = total - passed
        tool_correct = sum(1 for r in results if r.tool_correct)
        tool_accuracy = tool_correct / total if total > 0 else 0.0
        avg_dur = sum(r.duration_ms for r in results) / total if total > 0 else 0.0

        return ModelReport(
            model=model,
            total=total,
            passed=passed,
            failed=failed,
            tool_accuracy=tool_accuracy,
            avg_duration_ms=avg_dur,
            results=results,
        )


# ──────────────────────────────────────────────
# Reporter
# ──────────────────────────────────────────────

class EvalReporter:
    """Форматирование и сохранение результатов."""

    @staticmethod
    def print_report(reports: list[ModelReport], detailed: bool = False):
        """Вывести отчёт в консоль."""
        print("\n" + "=" * 70)
        print("  EVAL HARNESS — BASELINE REPORT")
        print("=" * 70)

        # Сводная таблица
        print(f"\n{'Модель':<40} {'Всего':>6} {'✅':>6} {'❌':>6} {'Точность':>10} {'Ср.мс':>8}")
        print("-" * 70)
        for r in sorted(reports, key=lambda x: x.tool_accuracy, reverse=True):
            acc = f"{r.tool_accuracy:.0%}"
            print(f"{r.model:<40} {r.total:>6} {r.passed:>6} {r.failed:>6} {acc:>10} {r.avg_duration_ms:>7.0f}")

        # Общий итог
        all_results = [res for r in reports for res in r.results]
        total = len(all_results)
        passed = sum(1 for r in all_results if r.overall_pass)
        print(f"\n{'ИТОГО':<40} {total:>6} {passed:>6} {total - passed:>6} {passed / total:.0%}") if total else None

        # Детали по кейсам (опционально)
        if detailed:
            print("\n\n  Детали по кейсам:")
            print("-" * 70)
            failed_cases = [r for r in all_results if not r.overall_pass]
            for r in failed_cases:
                print(f"\n  [{r.model}] {r.case_id}: ❌")
                print(f"    Ожидался: tool={r.expected_tool}, args={r.expected_args}")
                print(f"    Получено:  tool={r.parsed_tool}")
                print(f"    Ответ ({len(r.raw_response)} chars): {r.raw_response[:200]}")

    @staticmethod
    def save_report(reports: list[ModelReport], path: str = "eval_results.json"):
        """Сохранить результаты в JSON."""
        data = []
        for r in reports:
            data.append({
                "model": r.model,
                "total": r.total,
                "passed": r.passed,
                "failed": r.failed,
                "tool_accuracy": r.tool_accuracy,
                "avg_duration_ms": r.avg_duration_ms,
                "results": [
                    {
                        "case_id": res.case_id,
                        "overall_pass": res.overall_pass,
                        "tool_correct": res.tool_correct,
                        "args_correct": res.args_correct,
                        "expected_tool": res.expected_tool,
                        "parsed_tool": res.parsed_tool,
                        "expected_args": res.expected_args,
                        "parsed_args": res.parsed_args,
                        "duration_ms": res.duration_ms,
                        "error": res.error,
                        "raw_response_preview": res.raw_response[:300],
                    }
                    for res in r.results
                ],
            })

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\n📄 Результаты сохранены в {path}")

    @staticmethod
    def load_report(path: str = "eval_results.json") -> list[ModelReport]:
        """Загрузить результаты из JSON."""
        # Для простоты возвращаем сырые данные — вызывающий сам решает
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)


# ──────────────────────────────────────────────
# Загрузка моделей из Ollama
# ──────────────────────────────────────────────

def get_available_models() -> list[str]:
    """Получить список доступных моделей из Ollama."""
    import requests
    try:
        resp = requests.get("http://192.168.5.7:11434/api/tags", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        return [m["name"] for m in data.get("models", [])]
    except Exception as e:
        print(f"[yellow]⚠️ Не удалось получить список моделей: {e}[/yellow]")
        return []


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Eval Harness — замер точности вызова инструментов")
    parser.add_argument("models", nargs="*", help="Модели для тестирования")
    parser.add_argument("--all", action="store_true", help="Все доступные модели")
    parser.add_argument("--quick", action="store_true",
                        help="Только малые модели (≤14B)")
    parser.add_argument("--detailed", action="store_true",
                        help="Показать детали по упавшим кейсам")
    parser.add_argument("--output", default="eval_results.json",
                        help="Файл для сохранения результатов")
    parser.add_argument("--save-only", action="store_true",
                        help="Не выводить в консоль, только сохранить")

    args = parser.parse_args()

    # Определяем список моделей
    models = args.models
    if args.all:
        models = get_available_models()
    elif args.quick:
        all_models = get_available_models()
        # Только chat/code модели — исключаем embedding
        skip_keywords = ["embed", "bge", "mxbai", "nomic", "paraphrase",
                         "enbeddrus", "llava", "bakllava"]
        # Модели ≤14B — исключаем большие (>14B)
        big_sizes = ["14b", "16b", "22b", "30b", "32b", "34b"]
        # Приоритет: сначала компактные кодер-модели (7B-9B), потом general
        models = [m for m in all_models
                  if not any(k in m.lower() for k in skip_keywords)
                  and not any(s in m.lower() for s in big_sizes)]
        # Берём не более 8 для быстрого baseline
        if len(models) > 8:
            models = models[:8]
        if not models:
            models = [m for m in all_models if not any(k in m.lower()
                       for k in skip_keywords)][:6]
    elif not models:
        models = get_available_models()

    if not models:
        print("Нет моделей для тестирования. Укажите модели или --all/--quick.")
        sys.exit(1)

    print(f"🧪 Eval Harness — {len(models)} моделей, {len(_EVAL_CASES)} кейсов")
    print(f"   Модели: {', '.join(models)}")
    print()

    runner = EvalRunner(models=models)
    try:
        reports = runner.run_all(progress=True)
    except KeyboardInterrupt:
        print("\n\n⚠️ Прервано пользователем.")
        return

    reporter = EvalReporter()
    if not args.save_only:
        reporter.print_report(reports, detailed=args.detailed)

    if args.output:
        reporter.save_report(reports, path=args.output)


if __name__ == "__main__":
    main()