# -*- coding: utf-8 -*-
# modules/checkpoint_manager.py — Сохранение/восстановление состояния миграции (Фаза 6.3)

import json
import os
from datetime import datetime


DEFAULT_CHECKPOINT_DIR = "checkpoints"


class CheckpointManager:
    """Сохранение/восстановление состояния миграции между сессиями.

    Пишет чекпоинты в JSON-файлы в checkpoints/ директории.
    Позволяет возобновить прерванную миграцию.
    """

    def __init__(self, project_name: str, checkpoint_dir: str = None):
        self.project_name = project_name
        self.checkpoint_dir = checkpoint_dir or os.path.join(
            os.getcwd(), DEFAULT_CHECKPOINT_DIR
        )
        self._checkpoint_file = os.path.join(
            self.checkpoint_dir, f"{project_name}.json"
        )
        os.makedirs(self.checkpoint_dir, exist_ok=True)

        # Текущее состояние в памяти
        self._state: dict = self._load()

    # ── Загрузка/сохранение ──────────────────────────────────────────

    def _load(self) -> dict:
        """Загрузить чекпоинт из файла."""
        if os.path.exists(self._checkpoint_file):
            try:
                with open(self._checkpoint_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, Exception):
                pass
        return self._new_state()

    def _new_state(self) -> dict:
        """Создать пустое состояние."""
        return {
            "project_name": self.project_name,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "tasks": {},
            "summary": {
                "total": 0,
                "completed": 0,
                "failed": 0,
                "pending": 0,
                "in_progress": 0,
            },
            "session_history": [],
        }

    def _save(self):
        """Сохранить текущее состояние в файл."""
        self._state["updated_at"] = datetime.now().isoformat()
        # Обновляем сводку
        tasks = self._state.get("tasks", {})
        s = self._state.setdefault("summary", {})
        s["total"] = len(tasks)
        statuses = [t.get("status", "pending") for t in tasks.values()]
        s["completed"] = statuses.count("completed")
        s["failed"] = statuses.count("failed")
        s["pending"] = statuses.count("pending")
        s["in_progress"] = statuses.count("in_progress")

        with open(self._checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(self._state, f, indent=2, ensure_ascii=False)

    # ── Публичные методы ────────────────────────────────────────────

    def save_checkpoint(self, task_id: int, status: str,
                       details: dict = None):
        """Сохранить состояние одной задачи.

        Args:
            task_id: ID задачи
            status: "completed" | "failed" | "in_progress" | "pending"
            details: доп. информация (ошибка, время, файлы)
        """
        tasks = self._state.setdefault("tasks", {})
        tasks[str(task_id)] = {
            "status": status,
            "updated_at": datetime.now().isoformat(),
            "details": details or {},
        }
        self._save()

    def can_resume(self) -> bool:
        """Можно ли возобновить прерванную миграцию.

        Возвращает True, если есть незавершённые задачи.
        """
        if not self._state.get("tasks"):
            return False
        s = self._state.get("summary", {})
        return s.get("pending", 0) > 0 or s.get("in_progress", 0) > 0

    def load_checkpoint(self) -> dict:
        """Загрузить чекпоинт.

        Returns:
            dict с состоянием миграции
        """
        return dict(self._state)

    def get_failed_tasks(self) -> list[tuple[int, dict]]:
        """Вернуть список упавших задач для повторного запуска."""
        failed = []
        for tid_str, info in self._state.get("tasks", {}).items():
            if info.get("status") == "failed":
                failed.append((int(tid_str), info))
        return failed

    def get_completed_tasks(self) -> list[int]:
        """Вернуть список ID выполненных задач."""
        completed = []
        for tid_str, info in self._state.get("tasks", {}).items():
            if info.get("status") == "completed":
                completed.append(int(tid_str))
        return completed

    def log_session_event(self, event_type: str, message: str):
        """Записать событие сессии в историю."""
        history = self._state.setdefault("session_history", [])
        history.append({
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            "message": message,
        })
        self._save()

    def get_progress_report(self, tasks_json: dict = None) -> str:
        """Сформировать текстовый отчёт о прогрессе.

        Args:
            tasks_json: содержимое tasks.json для доп. информации

        Returns:
            многострочный отчёт
        """
        s = self._state.get("summary", {})
        lines = [
            f"📊 Отчёт о миграции: {self.project_name}",
            f"   Всего задач: {s.get('total', 0)}",
            f"   Выполнено: {s.get('completed', 0)} ✅",
            f"   Провалено: {s.get('failed', 0)} ❌",
            f"   В процессе: {s.get('in_progress', 0)} 🔄",
            f"   Ожидает: {s.get('pending', 0)} ⏳",
            f"",
            f"   Прогресс: {self._progress_bar(s)}",
            f"",
        ]

        # Детали по каждой задаче из tasks.json
        if tasks_json:
            lines.append("📋 Детали задач:")
            for t in tasks_json.get("tasks", []):
                tid = t["id"]
                task_info = self._state.get("tasks", {}).get(str(tid), {})
                status = task_info.get("status", t.get("status", "unknown"))
                icon = {"completed": "✅", "failed": "❌", "in_progress": "🔄",
                        "pending": "⏳"}.get(status, "❓")
                lines.append(f"   {icon} Задача #{tid}: {t['target_file']} [{status}]")

        return "\n".join(lines)

    def _progress_bar(self, summary: dict, width: int = 20) -> str:
        """Сформировать прогресс-бар."""
        total = summary.get("total", 1) or 1
        done = summary.get("completed", 0)
        filled = int(done / total * width)
        bar = "█" * filled + "░" * (width - filled)
        return f"[{bar}] {done}/{total}"

    def _build_task_report_line(self, task: dict) -> str:
        """Одна строка отчёта для задачи."""
        tid = task["id"]
        info = self._state.get("tasks", {}).get(str(tid), {})
        status = info.get("status", task.get("status", "unknown"))
        icons = {
            "completed": "✅",
            "failed": "❌",
            "in_progress": "🔄",
            "pending": "⏳",
        }
        icon = icons.get(status, "❓")

        effort = task.get("effort", "?")
        layer = task.get("layer", "?")
        deps = task.get("dependencies", [])

        extra = ""
        if info.get("details", {}).get("error"):
            extra = f" — {info['details']['error'][:80]}"
        if status == "completed":
            elapsed = info.get("details", {}).get("duration_seconds")
            if elapsed:
                extra = f" ({elapsed:.0f}с)"

        dep_str = f" [зависит от: {len(deps)} файлов]" if deps else " [корень]"
        return f"{icon} Задача #{tid}: {task['target_file']} ({effort}, слой {layer}){dep_str}{extra}"


def generate_migration_report(checkpoint_path: str, tasks_path: str) -> str:
    """Сгенерировать финальный отчёт из файлов чекпоинта и tasks.json.

    Args:
        checkpoint_path: путь к файлу чекпоинта
        tasks_path: путь к tasks.json

    Returns:
        многострочный отчёт
    """
    try:
        with open(checkpoint_path, "r", encoding="utf-8") as f:
            checkpoint = json.load(f)
    except Exception as e:
        return f"❌ ОШИБКА: Не удалось загрузить {checkpoint_path}\n{e}"

    try:
        with open(tasks_path, "r", encoding="utf-8") as f:
            tasks_json = json.load(f)
    except Exception as e:
        return f"❌ ОШИБКА: Не удалось загрузить {tasks_path}\n{e}"

    from modules.progress_reporter import ProgressReporter
    reporter = ProgressReporter()
    return reporter.format_report(checkpoint, tasks_json)