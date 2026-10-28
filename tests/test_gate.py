# -*- coding: utf-8 -*-
# tests/test_gate.py — Тесты для Gate (Фаза 4.3)

import unittest
import unittest.mock
import sys
import os
import json
import tempfile
import subprocess

from tests import *  # noqa: sys.path
import tempfile
import json


class TestGateError(unittest.TestCase):

    def test_gate_error_is_exception(self):
        from modules.gate import GateError
        self.assertTrue(issubclass(GateError, Exception))


class TestGateInit(unittest.TestCase):
    """Gate.__init__."""

    def test_default_command(self):
        from modules.gate import Gate
        gate = Gate()
        self.assertEqual(gate.test_command, [sys.executable, "test_core.py"])

    def test_custom_command(self):
        from modules.gate import Gate
        gate = Gate(test_command=["echo", "ok"])
        self.assertEqual(gate.test_command, ["echo", "ok"])

    def test_custom_eval_path(self):
        from modules.gate import Gate
        gate = Gate(eval_results_path="/tmp/eval.json", baseline_path="/tmp/baseline.json")
        self.assertEqual(gate.eval_results_path, "/tmp/eval.json")
        self.assertEqual(gate.baseline_path, "/tmp/baseline.json")


class TestGateCheck(unittest.TestCase):
    """Gate.check."""

    def test_kernel_denied(self):
        from modules.gate import Gate
        gate = Gate()
        result = gate.check("test", zone="kernel")
        self.assertFalse(result)
        results = gate.get_results()
        self.assertIn("DENIED", results["verdict"])

    def test_autonomous_tests_pass(self):
        from modules.gate import Gate
        gate = Gate(test_command=[sys.executable, "-c", "exit(0)"])
        result = gate.check("test", zone="autonomous")
        self.assertTrue(result)
        results = gate.get_results()
        self.assertEqual(results["verdict"], "ACCEPTED")

    def test_tests_fail_denied(self):
        from modules.gate import Gate
        gate = Gate(test_command=[sys.executable, "-c", "exit(1)"])
        result = gate.check("test", zone="autonomous")
        self.assertFalse(result)
        results = gate.get_results()
        self.assertIn("DENIED", results["verdict"])

    @unittest.mock.patch("modules.gate.Gate._ask_human", return_value=True)
    def test_supervised_with_human_approval(self, mock_ask):
        from modules.gate import Gate
        gate = Gate(test_command=[sys.executable, "-c", "exit(0)"],
                    eval_results_path="/nonexistent/eval.json")
        result = gate.check("test", zone="supervised")
        self.assertTrue(result)

    @unittest.mock.patch("modules.gate.Gate._ask_human", return_value=False)
    def test_supervised_human_rejected(self, mock_ask):
        from modules.gate import Gate
        gate = Gate(test_command=[sys.executable, "-c", "exit(0)"],
                    eval_results_path="/nonexistent/eval.json")
        result = gate.check("test", zone="supervised")
        self.assertFalse(result)

    @unittest.mock.patch("modules.gate.Gate._ask_human", return_value=True)
    def test_require_human_flag(self, mock_ask):
        from modules.gate import Gate
        gate = Gate(test_command=[sys.executable, "-c", "exit(0)"],
                    eval_results_path="/nonexistent/eval.json")
        result = gate.check("test", require_human=True)
        self.assertTrue(result)

    def test_check_returns_results(self):
        from modules.gate import Gate
        gate = Gate(test_command=[sys.executable, "-c", "exit(0)"])
        gate.check("test", zone="autonomous")
        results = gate.get_results()
        self.assertIn("change_name", results)
        self.assertIn("zone", results)
        self.assertIn("verdict", results)
        self.assertIn("checks", results)

    def test_check_eval_regression_denied(self):
        """eval деградация в check() → DENIED."""
        from modules.gate import Gate
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"accuracy": 70.0}, f)
            current = f.name
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"accuracy": 85.0}, f)
            baseline = f.name
        try:
            gate = Gate(test_command=[sys.executable, "-c", "exit(0)"],
                        eval_results_path=current, baseline_path=baseline)
            result = gate.check("eval_regression_test")
            self.assertFalse(result)
            self.assertIn("DENIED", gate.get_results()["verdict"])
        finally:
            os.unlink(current)
            os.unlink(baseline)

    def test_check_timeout_logged(self):
        """_check_tests timeout записывается в results."""
        from modules.gate import Gate
        gate = Gate(test_command=["sleep", "10"])
        gate._results = {"checks": {}}
        with unittest.mock.patch("modules.gate.subprocess.run",
                                 side_effect=subprocess.TimeoutExpired("cmd", 120)):
            gate._check_tests()
        self.assertIn("timeout", gate._results["checks"]["tests"]["error"])

    def test_check_called_with_no_results(self):
        """check() без _check_eval вызывает _check_tests."""
        from modules.gate import Gate
        gate = Gate(test_command=[sys.executable, "-c", "exit(0)"],
                    eval_results_path="/nonexistent/eval.json")
        result = gate.check("no_eval_test")
        self.assertTrue(result)


class TestCheckEval(unittest.TestCase):
    """Gate._check_eval."""

    def _make_gate(self, *args, **kwargs):
        from modules.gate import Gate
        gate = Gate(*args, **kwargs)
        # _check_eval требует _results["checks"]
        gate._results = {"checks": {}}
        return gate

    def test_no_eval_file_skips(self):
        gate = self._make_gate(test_command=[sys.executable, "-c", "exit(0)"],
                               eval_results_path="/nonexistent/eval.json")
        result = gate._check_eval()
        self.assertTrue(result)

    def test_no_baseline_skips(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"accuracy": 80.0}, f)
            eval_path = f.name
        try:
            gate = self._make_gate(eval_results_path=eval_path,
                                   baseline_path="/nonexistent/baseline.json")
            result = gate._check_eval()
            self.assertTrue(result)
        finally:
            os.unlink(eval_path)

    def test_json_decode_error_returns_false(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not json")
            bad_path = f.name
        try:
            gate = self._make_gate(eval_results_path=bad_path,
                                   baseline_path=bad_path)
            result = gate._check_eval()
            self.assertFalse(result)
        finally:
            os.unlink(bad_path)

    def test_accuracy_degradation_detected(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"accuracy": 70.0}, f)
            current = f.name
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"accuracy": 85.0}, f)
            baseline = f.name
        try:
            gate = self._make_gate(eval_results_path=current,
                                   baseline_path=baseline)
            result = gate._check_eval()
            self.assertFalse(result)  # 70 < 85 - 5
        finally:
            os.unlink(current)
            os.unlink(baseline)

    def test_accuracy_within_threshold(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"accuracy": 82.0}, f)
            current = f.name
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"accuracy": 85.0}, f)
            baseline = f.name
        try:
            gate = self._make_gate(eval_results_path=current,
                                   baseline_path=baseline)
            result = gate._check_eval()
            self.assertTrue(result)  # 82 >= 85 - 5 = 80
        finally:
            os.unlink(current)
            os.unlink(baseline)


class TestExtractAccuracy(unittest.TestCase):
    """Gate._extract_accuracy."""

    def setUp(self):
        from modules.gate import Gate
        self.gate = Gate()

    def test_overall_accuracy_key(self):
        result = self.gate._extract_accuracy({"overall_accuracy": 85.0})
        self.assertEqual(result, 85.0)

    def test_accuracy_key(self):
        result = self.gate._extract_accuracy({"accuracy": 75.5})
        self.assertEqual(result, 75.5)

    def test_summary_accuracy(self):
        result = self.gate._extract_accuracy({"summary": {"accuracy": 90.0}})
        self.assertEqual(result, 90.0)

    def test_models_accuracy(self):
        result = self.gate._extract_accuracy({
            "models": {"a": {"accuracy": 80.0}, "b": {"accuracy": 90.0}}
        })
        self.assertEqual(result, 85.0)

    def test_no_accuracy_returns_none(self):
        result = self.gate._extract_accuracy({"foo": "bar"})
        self.assertIsNone(result)


class TestCheckTestsOnly(unittest.TestCase):
    """Gate.check_tests_only."""

    def test_tests_pass(self):
        from modules.gate import Gate
        gate = Gate(test_command=[sys.executable, "-c", "exit(0)"])
        result = gate.check_tests_only()
        self.assertTrue(result)

    def test_tests_fail(self):
        from modules.gate import Gate
        gate = Gate(test_command=[sys.executable, "-c", "exit(1)"])
        result = gate.check_tests_only()
        self.assertFalse(result)


class TestSaveReport(unittest.TestCase):
    """Gate._save_report."""

    def tearDown(self):
        import shutil
        shutil.rmtree("traces", ignore_errors=True)

    def test_save_report_creates_file(self):
        from modules.gate import Gate
        gate = Gate(test_command=[sys.executable, "-c", "exit(0)"])
        gate.check("test_report")
        self.assertTrue(os.path.exists("traces/gate"))
        files = os.listdir("traces/gate")
        self.assertGreater(len(files), 0)


if __name__ == "__main__":
    unittest.main()