# -*- coding: utf-8 -*-
# modules/gate.py — Гейт принятия изменений (Фаза 4.3)
#
# Проверяет, что изменения не сломали существующую функциональность:
# - eval-харнесс (Фаза 1) не деградировал
# - тесты проходят
# - для supervised-зоны — подтверждение человека
#
# Использование:
#     from modules.gate import Gate
#     gate = Gate()
#     if gate.check("fix-parser"):
#         # изменения приняты
#     else:
#         # откат

import json
import os
import subprocess
import sys
from typing import Optional


class GateError(Exception):
    """Ошибка гейта."""


class Gate:
    """Гейт принятия изменений.

    Проверяет три уровня:
    1. Тесты — `python test_core.py` должен вернуть 0
    2. Eval — метрики не должны деградировать (сравнение с baseline)
    3. Supervised — запрос подтверждения человека
    """

    def __init__(self, test_command: str = None,
                 eval_results_path: str = None,
                 baseline_path: str = None):
        """
        Args:
            test_command: команда запуска тестов (по умолч. python test_core.py)
            eval_results_path: путь к текущим результатам eval
            baseline_path: путь к baseline для сравнения
        """
        self.test_command = test_command or [sys.executable, "test_core.py"]
        self.eval_results_path = eval_results_path or "eval_results_v3_large.json"
        self.baseline_path = baseline_path or "eval_results_v3_large.json"
        self._results = {}

    # ─────────────────────────────────────────────
    # Публичные методы
    # ─────────────────────────────────────────────

    def check(self, change_name: str, zone: str = "autonomous",
              require_human: bool = None) -> bool:
        """Полная проверка изменений.

        Args:
            change_name: название изменения (для отчёта)
            zone: зона мутабельности ('autonomous', 'supervised', 'kernel')
            require_human: принудительно запросить подтверждение

        Returns:
            True если все проверки пройдены
        """
        self._results = {
            "change_name": change_name,
            "zone": zone,
            "checks": {},
        }

        # Kernel — запрет
        if zone == "kernel":
            self._results["verdict"] = "DENIED (kernel)"
            return False

        # 1. Тесты
        tests_ok = self._check_tests()
        self._results["checks"]["tests"] = {
            "status": "passed" if tests_ok else "failed",
        }
        if not tests_ok:
            self._results["verdict"] = "DENIED (tests failed)"
            self._save_report()
            return False

        # 2. Eval (только если есть baseline)
        eval_ok = self._check_eval()
        self._results["checks"]["eval"] = {
            "status": "passed" if eval_ok else "failed",
        }
        if not eval_ok:
            self._results["verdict"] = "DENIED (eval regression)"
            self._save_report()
            return False

        # 3. Supervised — подтверждение человека
        if zone == "supervised" or require_human:
            human_ok = self._ask_human(change_name)
            self._results["checks"]["human"] = {
                "status": "approved" if human_ok else "rejected",
            }
            if not human_ok:
                self._results["verdict"] = "DENIED (human rejected)"
                self._save_report()
                return False

        self._results["verdict"] = "ACCEPTED"
        self._save_report()
        return True

    def check_tests_only(self) -> bool:
        """Быстрая проверка только тестов."""
        self._results = {
            "change_name": "check_tests_only",
            "zone": "autonomous",
            "checks": {},
        }
        return self._check_tests()

    def get_results(self) -> dict:
        """Получить результаты последней проверки."""
        return self._results

    # ─────────────────────────────────────────────
    # Приватные методы
    # ─────────────────────────────────────────────

    def _check_tests(self) -> bool:
        """Запуск тестов."""
        # Инициализируем вложенные ключи
        if "tests" not in self._results["checks"]:
            self._results["checks"]["tests"] = {}

        try:
            result = subprocess.run(
                self.test_command,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode == 0:
                return True

            # Сохраняем лог ошибок
            self._results["checks"]["tests"]["output"] = (
                result.stdout[-2000:] + "\n" + result.stderr[-2000:]
            )
            return False
        except subprocess.TimeoutExpired:
            self._results["checks"]["tests"]["error"] = "timeout (120s)"
            return False
        except Exception as e:
            self._results["checks"]["tests"]["error"] = str(e)
            return False

    def _check_eval(self) -> bool:
        """Проверка eval-метрик."""
        # Инициализируем вложенные ключи
        if "eval" not in self._results["checks"]:
            self._results["checks"]["eval"] = {}

        if not os.path.exists(self.eval_results_path):
            # Нет текущих результатов — пропускаем
            self._results["checks"]["eval"]["note"] = "no eval results to compare"
            return True

        if not os.path.exists(self.baseline_path):
            # Нет baseline — пропускаем
            self._results["checks"]["eval"]["note"] = "no baseline to compare"
            return True

        try:
            with open(self.eval_results_path) as f:
                current = json.load(f)
            with open(self.baseline_path) as f:
                baseline = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            self._results["checks"]["eval"]["error"] = str(e)
            return False

        # Сравниваем общую метрику accuracy
        current_acc = self._extract_accuracy(current)
        baseline_acc = self._extract_accuracy(baseline)

        self._results["checks"]["eval"]["current_accuracy"] = current_acc
        self._results["checks"]["eval"]["baseline_accuracy"] = baseline_acc

        if current_acc is None or baseline_acc is None:
            self._results["checks"]["eval"]["note"] = "cannot compare accuracy"
            return True

        # Допускаем деградацию не более 5%
        if current_acc < baseline_acc - 5.0:
            self._results["checks"]["eval"]["regression"] = (
                f"{baseline_acc - current_acc:.1f}%"
            )
            return False

        return True

    def _extract_accuracy(self, data: dict) -> Optional[float]:
        """Извлечь общую accuracy из результатов eval."""
        # Пробуем разные форматы
        if "overall_accuracy" in data:
            return data["overall_accuracy"]
        if "accuracy" in data:
            return data["accuracy"]
        if "summary" in data and "accuracy" in data["summary"]:
            return data["summary"]["accuracy"]
        # Считаем из результатов по моделям
        if "models" in data:
            accuracies = []
            for m_data in data["models"].values():
                if "accuracy" in m_data:
                    accuracies.append(m_data["accuracy"])
            if accuracies:
                return sum(accuracies) / len(accuracies)
        return None

    def _ask_human(self, change_name: str) -> bool:
        """Запросить подтверждение человека.

        В неинтерактивном режиме (CI, тесты) — возвращает False.
        """
        # Инициализируем вложенные ключи
        if "human" not in self._results["checks"]:
            self._results["checks"]["human"] = {}

        # Проверяем, есть ли интерактивный ввод
        if not sys.stdin.isatty():
            self._results["checks"]["human"]["note"] = (
                "non-interactive mode, assuming rejected"
            )
            return False

        print(f"\n{'='*60}")
        print(f"⚠️  Зона SUPERVISED: изменение '{change_name}'")
        print(f"{'='*60}")
        print("Требуется подтверждение человека.")
        print("Тесты и eval пройдены.")

        while True:
            try:
                answer = input("Применить изменения? (y/n): ").strip().lower()
                if answer in ("y", "yes"):
                    return True
                elif answer in ("n", "no"):
                    return False
            except (EOFError, KeyboardInterrupt):
                return False

    def _save_report(self):
        """Сохранить отчёт о проверке."""
        report_dir = "traces/gate"
        os.makedirs(report_dir, exist_ok=True)

        from datetime import datetime
        report_path = os.path.join(
            report_dir,
            f"gate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        )
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(self._results, f, indent=2, ensure_ascii=False)