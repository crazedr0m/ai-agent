# -*- coding: utf-8 -*-
# tests/test_tracer.py — Тесты для TraceSession и StepTrace

import unittest
import os
import json
import tempfile
import shutil

from tests import *  # noqa: sys.path


class TestTracer(unittest.TestCase):
    """Тесты для TraceSession и StepTrace."""

    def setUp(self):
        self.traces_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.traces_dir, ignore_errors=True)

    def test_step_trace_to_dict(self):
        """StepTrace сериализуется в dict."""
        from modules.tracer import StepTrace

        step = StepTrace("llm_call", "test content",
                         {"model": "qwen2.5-coder:14b"})
        data = step.to_dict()
        self.assertEqual(data["type"], "llm_call")
        self.assertEqual(data["content"], "test content")
        self.assertEqual(data["metadata"]["model"], "qwen2.5-coder:14b")
        self.assertIn("timestamp", data)

    def test_step_trace_from_dict(self):
        """StepTrace десериализуется из dict."""
        from modules.tracer import StepTrace

        data = {
            "type": "tool_call",
            "content": "list_dir .",
            "metadata": {"tool_name": "list_dir"},
            "timestamp": "2026-01-01T00:00:00Z"
        }
        step = StepTrace.from_dict(data)
        self.assertEqual(step.step_type, "tool_call")
        self.assertEqual(step.content, "list_dir .")
        self.assertEqual(step.metadata["tool_name"], "list_dir")

    def test_trace_session_writes_jsonl(self):
        """TraceSession пишет JSONL-файл."""
        from modules.tracer import TraceSession

        with TraceSession("test_agent",
                          traces_dir=self.traces_dir) as session:
            session.log_llm_call("system prompt", model="test-model")
            session.log_tool_call("list_dir", "/tmp", "file1\nfile2")
            session.log_final("Done")

        self.assertTrue(os.path.exists(session.jsonl_path))

        with open(session.jsonl_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        self.assertGreaterEqual(len(lines), 4)

        records = [json.loads(line.strip()) for line in lines if line.strip()]
        types = [r["type"] for r in records]
        self.assertIn("__session_start__", types)
        self.assertIn("llm_call", types)
        self.assertIn("tool_call", types)
        self.assertIn("tool_result", types)
        self.assertIn("final", types)
        self.assertIn("__session_end__", types)

    def test_trace_session_context_manager(self):
        """TraceSession работает как context manager."""
        from modules.tracer import TraceSession, StepTrace

        with TraceSession("test_ctx",
                          traces_dir=self.traces_dir) as session:
            self.assertFalse(session._closed)
            session.log_step(StepTrace("system", "test"))

        self.assertTrue(session._closed)

    def test_trace_session_rotation(self):
        """TraceSession удаляет старые сессии при превышении лимита."""
        from modules.tracer import TraceSession

        max_sessions = 3
        sessions = []
        for i in range(max_sessions + 2):
            session = TraceSession(f"test_{i}",
                                   traces_dir=self.traces_dir,
                                   max_sessions=max_sessions)
            session.close()
            sessions.append(session)

        remaining = [d for d in os.listdir(self.traces_dir)
                     if d.startswith("session_")]
        self.assertLessEqual(len(remaining), max_sessions)


if __name__ == "__main__":
    unittest.main()