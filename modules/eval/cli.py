# -*- coding: utf-8 -*-
# modules/eval/cli.py — CLI для eval-харнесса

import sys

from modules.eval.runner import EvalRunner
from modules.eval.reporter import EvalReporter
from modules.eval.cases import EVAL_CASES
from modules.eval.utils import get_available_models


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
        skip_keywords = ["embed", "bge", "mxbai", "nomic", "paraphrase",
                         "enbeddrus", "llava", "bakllava"]
        big_sizes = ["14b", "16b", "22b", "30b", "32b", "34b"]
        models = [m for m in all_models
                  if not any(k in m.lower() for k in skip_keywords)
                  and not any(s in m.lower() for s in big_sizes)]
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

    print(f"🧪 Eval Harness — {len(models)} моделей, {len(EVAL_CASES)} кейсов")
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