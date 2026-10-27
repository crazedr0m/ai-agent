# -*- coding: utf-8 -*-
# modules/eval/reporter.py — Форматирование и сохранение результатов eval

import json

from modules.eval.results import ModelReport


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
        if total:
            print(f"\n{'ИТОГО':<40} {total:>6} {passed:>6} {total - passed:>6} {passed / total:.0%}")

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
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)