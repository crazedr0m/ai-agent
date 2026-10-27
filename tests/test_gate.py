# -*- coding: utf-8 -*-
# tests/test_gate.py — Тесты для Gate (Фаза 4.3)

import unittest
import sys

from tests import *  # noqa: sys.path


class TestPhase4Gate(unittest.TestCase):
    """Тесты для Gate (Фаза 4.3)."""

    def test_gate_check_tests_only(self):
        """check_tests_only запускает тесты (через echo)."""
        from modules.gate import Gate
        gate = Gate(test_command=[sys.executable, "-c", "exit(0)"])
        result = gate.check_tests_only()
        self.assertTrue(result)

    def test_gate_kernel_denied(self):
        """kernel-зона всегда DENIED."""
        from modules.gate import Gate
        gate = Gate()
        result = gate.check("test", zone="kernel")
        self.assertFalse(result)

    def test_gate_autonomous_passes(self):
        """autonomous-зона проходит если тесты ок."""
        from modules.gate import Gate
        import sys
        gate = Gate(test_command=[sys.executable, "-c", "exit(0)"])
        result = gate.check("test", zone="autonomous")
        self.assertTrue(result)

    def test_gate_get_results(self):
        """get_results возвращает словарь."""
        from modules.gate import Gate
        import sys
        gate = Gate(test_command=[sys.executable, "-c", "exit(0)"])
        gate.check("test", zone="autonomous")
        results = gate.get_results()
        self.assertIn("verdict", results)
        self.assertIn("checks", results)


if __name__ == "__main__":
    unittest.main()