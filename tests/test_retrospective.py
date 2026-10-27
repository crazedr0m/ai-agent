# -*- coding: utf-8 -*-
# tests/test_retrospective.py — Тесты для Retrospective (Фаза 4.4)

import unittest
import os
import json
import tempfile

from tests import *  # noqa: sys.path


class TestPhase4Retrospective(unittest.TestCase):
    """Тесты для Retrospective (Фаза 4.4)."""

    def test_retrospective_empty(self):
        """Ретроспектива без трейсов не падает."""
        from modules.retrospective import Retrospective
        retro = Retrospective(traces_dir="/nonexistent/traces")
        report = retro.analyze()
        self.assertEqual(report.total_sessions, 0)
        self.assertEqual(report.total_errors, 0)

    def test_retro_report_summary(self):
        """RetroReport.summary возвращает строку."""
        from modules.retrospective import RetroReport
        report = RetroReport(total_sessions=1, total_errors=0, total_tool_calls=5)
        summary = report.summary
        self.assertIn("Ретроспектива", summary)
        self.assertIn("1", summary)

    def test_retro_report_save(self):
        """RetroReport.save() сохраняет JSON."""
        from modules.retrospective import RetroReport
        report = RetroReport(total_sessions=1, total_errors=2, total_tool_calls=3)
        report.add_finding("test", "test finding", 2, "fix it")
        tmpfile = tempfile.mktemp(suffix=".json")
        try:
            report.save(tmpfile)
            self.assertTrue(os.path.exists(tmpfile))
            with open(tmpfile) as f:
                data = json.load(f)
            self.assertEqual(data["total_sessions"], 1)
            self.assertEqual(len(data["findings"]), 1)
        finally:
            if os.path.exists(tmpfile):
                os.unlink(tmpfile)


if __name__ == "__main__":
    unittest.main()