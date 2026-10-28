# -*- coding: utf-8 -*-
# tests/test_migration_context.py — Тесты для modules/migration_context.py

import os
import tempfile
import unittest

from modules.migration_context import (
    CheckpointManager,
    ProgressReporter,
    FractionalMemory,
    generate_migration_report,
)


class TestCheckpointManager(unittest.TestCase):
    """Тесты для CheckpointManager."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.cm = CheckpointManager("test_project", checkpoint_dir=self.tmpdir)

    def test_initial_state(self):
        state = self.cm.load_checkpoint()
        self.assertEqual(state["project_name"], "test_project")
        self.assertEqual(state["summary"]["total"], 0)

    def test_save_and_load_checkpoint(self):
        self.cm.save_checkpoint(1, "completed", {"duration_seconds": 10})
        state = self.cm.load_checkpoint()
        self.assertEqual(state["summary"]["completed"], 1)
        self.assertEqual(state["summary"]["total"], 1)

    def test_can_resume_no_tasks(self):
        self.assertFalse(self.cm.can_resume())

    def test_can_resume_with_pending(self):
        self.cm.save_checkpoint(1, "pending")
        self.assertTrue(self.cm.can_resume())

    def test_get_failed_tasks(self):
        self.cm.save_checkpoint(1, "completed")
        self.cm.save_checkpoint(2, "failed", {"error": "test error"})
        failed = self.cm.get_failed_tasks()
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0][0], 2)

    def test_get_completed_tasks(self):
        self.cm.save_checkpoint(1, "completed")
        self.cm.save_checkpoint(2, "failed")
        completed = self.cm.get_completed_tasks()
        self.assertEqual(completed, [1])

    def test_log_session_event(self):
        self.cm.log_session_event("start", "Migration started")
        state = self.cm.load_checkpoint()
        self.assertEqual(len(state["session_history"]), 1)
        self.assertEqual(state["session_history"][0]["event"], "start")

    def test_persistence_between_instances(self):
        self.cm.save_checkpoint(1, "completed")
        # Создаём новый экземпляр для той же директории
        cm2 = CheckpointManager("test_project", checkpoint_dir=self.tmpdir)
        state = cm2.load_checkpoint()
        self.assertEqual(state["summary"]["completed"], 1)

    def test_get_progress_report_structure(self):
        self.cm.save_checkpoint(1, "completed")
        self.cm.save_checkpoint(2, "pending")
        report = self.cm.get_progress_report()
        self.assertIn("Отчёт о миграции", report)
        self.assertIn("test_project", report)

    def test_get_progress_report_with_tasks(self):
        self.cm.save_checkpoint(1, "completed")
        tasks_json = {
            "tasks": [
                {"id": 1, "target_file": "main.py", "status": "completed"},
            ]
        }
        report = self.cm.get_progress_report(tasks_json=tasks_json)
        self.assertIn("main.py", report)


class TestProgressReporter(unittest.TestCase):
    """Тесты для ProgressReporter."""

    def setUp(self):
        self.checkpoint = {
            "project_name": "test",
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T01:00:00",
            "tasks": {
                "1": {"status": "completed", "details": {"duration_seconds": 30}},
                "2": {"status": "failed", "details": {"error": "test error"}},
            },
            "summary": {"total": 2, "completed": 1, "failed": 1, "pending": 0, "in_progress": 0},
            "session_history": [
                {"timestamp": "2026-01-01T00:00:00", "event": "start", "message": "Начало"},
            ],
        }
        self.tasks_json = {
            "tasks": [
                {
                    "id": 1, "target_file": "main.py", "effort": "medium",
                    "layer": 0, "status": "completed",
                },
                {
                    "id": 2, "target_file": "utils.py", "effort": "low",
                    "layer": 0, "status": "failed",
                },
            ],
        }

    def test_format_report(self):
        report = ProgressReporter.format_report(self.checkpoint, self.tasks_json)
        self.assertIn("ОТЧЁТ О МИГРАЦИИ", report)
        self.assertIn("main.py", report)
        self.assertIn("utils.py", report)
        self.assertIn("50.0%", report)  # 1/2 = 50%

    def test_format_report_empty_tasks(self):
        report = ProgressReporter.format_report(self.checkpoint, {})
        self.assertIn("ОТЧЁТ О МИГРАЦИИ", report)


class TestGenerateMigrationReport(unittest.TestCase):
    """Тесты для generate_migration_report()."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def test_generate_report(self):
        checkpoint_path = os.path.join(self.tmpdir, "checkpoint.json")
        tasks_path = os.path.join(self.tmpdir, "tasks.json")

        with open(checkpoint_path, "w") as f:
            f.write('{"project_name": "test", "summary": {"total": 1, "completed": 0, "failed": 0, "pending": 1, "in_progress": 0}}')
        with open(tasks_path, "w") as f:
            f.write('{"tasks": [{"id": 1, "target_file": "main.py"}]}')

        report = generate_migration_report(checkpoint_path, tasks_path)
        self.assertIn("ОТЧЁТ О МИГРАЦИИ", report)

    def test_generate_report_missing_files(self):
        report = generate_migration_report("/nonexistent/checkpoint.json", "/nonexistent/tasks.json")
        self.assertIn("Не удалось загрузить", report)


if __name__ == "__main__":
    unittest.main()