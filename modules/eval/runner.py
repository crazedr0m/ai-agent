# -*- coding: utf-8 -*-
# modules/eval/runner.py — Прогон golden-кейсов на моделях

import time
from typing import Optional

import core
from core.core import ReActEngine

from modules.eval.cases import EvalCase, EVAL_CASES
from modules.eval.results import EvalResult, ModelReport


class EvalRunner:
    """Прогон golden-кейсов на моделях через текущий ReActEngine."""

    def __init__(self, models: list[str], cases: Optional[list[EvalCase]] = None,
                 timeout: int = 60, max_steps: int = 3):
        self.models = models
        self.cases = cases or EVAL_CASES
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