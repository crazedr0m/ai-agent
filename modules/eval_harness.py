# -*- coding: utf-8 -*-
# modules/eval_harness.py — Facade: реэкспорт из пакета modules/eval/
#
# После рефакторинга:
#   modules/eval/cases.py   — EvalCase, EVAL_SYSTEM, EVAL_CASES
#   modules/eval/results.py — EvalResult, ModelReport
#   modules/eval/runner.py  — EvalRunner
#   modules/eval/reporter.py — EvalReporter
#   modules/eval/utils.py   — get_available_models
#   modules/eval/cli.py     — main (CLI)

from modules.eval.cases import EvalCase, EVAL_SYSTEM, EVAL_CASES  # noqa: F401
from modules.eval.results import EvalResult, ModelReport  # noqa: F401
from modules.eval.runner import EvalRunner  # noqa: F401
from modules.eval.reporter import EvalReporter  # noqa: F401
from modules.eval.utils import get_available_models  # noqa: F401
from modules.eval.cli import main  # noqa: F401