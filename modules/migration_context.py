# -*- coding: utf-8 -*-
# modules/migration_context.py — Контекст миграции: чекпоинты, прогресс, LOG16 (Фаза 6.3/6.4)
#
# Предоставляет:
#   1. CheckpointManager — сохранение/восстановление состояния между сессиями
#   2. ProgressReporter — отчёт о прогрессе миграции
#   3. LOG16Integration — автоматическая запись/чтение ключевых фактов в Substrate
#   4. IncrementalCommiter — коммиты после каждой успешной задачи через Sandbox
#
# Использование:
#   from modules.migration_context import CheckpointManager, ProgressReporter
#   cm = CheckpointManager("project_name")
#   cm.save_checkpoint(task_id, status, details)
#   cm.can_resume() -> True/False
#   cm.load_checkpoint() -> dict

import json
import os
from datetime import datetime


# ─────────────────────────────────────────────
# CheckpointManager
# ─────────────────────────────────────────────

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

    # ── Загрузка/сохранение ──────────────────────────────────────

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

    # ── Публичные методы ──────────────────────────────────────────────

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


# ─────────────────────────────────────────────
# ProgressReporter
# ─────────────────────────────────────────────


class ProgressReporter:
    """Формирование отчётов о прогрессе миграции.

    Отличается от CheckpointManager тем, что работает на лету,
    без сохранения состояния.
    """

    @staticmethod
    def format_report(checkpoint: dict, tasks_json: dict) -> str:
        """Сформировать полный отчёт о миграции.

        Args:
            checkpoint: состояние из CheckpointManager.load_checkpoint()
            tasks_json: содержимое tasks.json

        Returns:
            многострочный отчёт
        """
        lines = []
        s = checkpoint.get("summary", {})

        # Заголовок
        lines.append("=" * 60)
        lines.append(f"📊 ОТЧЁТ О МИГРАЦИИ: {checkpoint.get('project_name', 'N/A')}")
        lines.append("=" * 60)
        lines.append(f"Создан: {checkpoint.get('created_at', 'N/A')}")
        lines.append(f"Обновлён: {checkpoint.get('updated_at', 'N/A')}")
        lines.append("")

        # Сводка
        total = s.get("total", 0)
        completed = s.get("completed", 0)
        failed = s.get("failed", 0)
        pending = s.get("pending", 0)
        pct = (completed / total * 100) if total > 0 else 0

        lines.append(f"📈 Прогресс: {pct:.1f}% ({completed}/{total})")
        lines.append(f"   ✅ Выполнено: {completed}")
        lines.append(f"   ❌ Провалено: {failed}")
        lines.append(f"   ⏳ Ожидает: {pending}")

        # Прогресс-бар
        bar_width = 30
        filled = int(completed / max(total, 1) * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)
        lines.append(f"   [{bar}]")
        lines.append("")

        # Сложность
        if tasks_json:
            high = sum(1 for t in tasks_json.get("tasks", []) if t.get("effort") == "high")
            medium = sum(1 for t in tasks_json.get("tasks", []) if t.get("effort") == "medium")
            low = sum(1 for t in tasks_json.get("tasks", []) if t.get("effort") == "low")
            lines.append(f"📐 Сложность: высок.{high} | сред.{medium} | низ.{low}")
            lines.append(f"📋 Слоёв зависимостей: {len(tasks_json.get('dependency_layers', []))}")
            lines.append("")

        # Детали по задачам
        lines.append("📋 ДЕТАЛИ ЗАДАЧ:")
        lines.append("-" * 60)

        if tasks_json:
            for task in tasks_json.get("tasks", []):
                tid = task["id"]
                task_info = checkpoint.get("tasks", {}).get(str(tid), {})
                status = task_info.get("status", task.get("status", "unknown"))
                icons = {
                    "completed": "✅",
                    "failed": "❌",
                    "in_progress": "🔄",
                    "pending": "⏳",
                }
                icon = icons.get(status, "❓")

                effort = task.get("effort", "?")
                layer = task.get("layer", "?")

                line = f"{icon} #{tid:3d} | {task['target_file'][:50]} | {effort!s:>6} | слой {layer!s:>2}"

                if status == "completed" and task_info.get("details", {}).get("duration_seonds"):
                    sec = task_info["details"]["duration_seconds"]
                    line += f" | {sec:.0f}с"

                if status == "failed" and task_info.get("details", {}).get("error"):
                    err = task_info["details"]["error"][:40]
                    line += f" | {err}"

                lines.append(line)

        # История сессий
        history = checkpoint.get("session_history", [])
        if history:
            lines.append("")
            lines.append("📜 ИСТОРИЯ СЕССИЙ:")
            for event in history[-10:]:  # последние 10
                lines.append(f"   [{event.get('timestamp', '')[:19]}] {event.get('event', '')}: {event.get('message', '')}")

        lines.append("")
        lines.append("=" * 60)
        return "\n".join(lines)


# ─────────────────────────────────────────────
# LOG16Integration (Фаза 6.4)
# ─────────────────────────────────────────────


class LOG16Integration:
    """Интеграция с LOG16 Substrate для долговременной памяти.

    Автоматически:
    - Сохраняет ключевые факты о проекте после каждой выполненной задачи
    - Загружает контекст предыдущих сессий при старте
    - Формирует структурированные записи для Substrate
    """

    def __init__(self, project_name: str, substrate_tool_prefix: str = "substrate__"):
        """
        Args:
            project_name: имя проекта для gate_trigger
            substrate_tool_prefix: префикс MCP-инструментов substrate
                                (substrate__ если через MCPManager)
        """
        self.project_name = project_name
        self._write_tool = f"{substrate_tool_prefix}write_to_substrate"
        self._query_tool = f"{substrate_tool_prefix}query_substrate"
        self._equalize_tool = f"{substrate_tool_prefix}equalize_memory"
        self._enabled = self._check_available()

    def _check_available(self) -> bool:
        """Проверить, доступны ли инструменты Substrate."""
        try:
            from core.core_tools import tool_registry
            return (
                self._write_tool in tool_registry._tools
                or "write_to_substrate" in tool_registry._tools
            )
        except Exception:
            return False

    def record_task_completed(self, task: dict, repo_map_summary: dict = None):
        """Записать факт о выполненной задаче в Substrate.

        Args:
            task: задача из tasks.json
            repo_map_summary: сводка из repo_map (опционально)
        """
        if not self._enabled:
            return

        file_path = task.get("target_file", "unknown")
        gate_trigger = f"migration {self.project_name} {file_path}"

        funcs = ", ".join(task.get("functions", [])[:5] or [])
        payload = (
            f"Migrated {file_path} ({task.get('effort', '?')} effort). "
            f"Functions: {funcs}"
        )

        try:
            from core.core_tools import execute_registered_tool
            execute_registered_tool(
                self._write_tool,
                payload=payload,
                gate_trigger=gate_trigger,
            )
        except Exception:
            pass  # LOG16 опционален

    def record_project_summary(self, repo_map: dict):
        """Записать сводку проекта в Substrate при старте."""
        if not self._enabled:
            return

        s = repo_map.get("summary", {})
        gate_trigger = f"migration {self.project_name} project_summary"
        payload = (
            f"Project {self.project_name}: {s.get('files_scanned', 0)} files, "
            f"{s.get('total_functions', 0)} functions, "
            f"{s.get('total_classes', 0)} classes, "
            f"{s.get('total_lines', 0)} lines"
        )

        try:
            from core.core_tools import execute_registered_tool
            execute_registered_tool(
                self._write_tool,
                payload=payload,
                gate_trigger=gate_trigger,
            )
        except Exception:
            pass

    def recall_project_context(self) -> str:
        """Загрузить конекст предыдущих сессий из Substrate.

        Returns:
            строка с факами о проете (ля LLM)
        """
        if not self._enabled:
            return ""

        try:
            from core.core_tools import execute_registered_tool
            result = execute_registered_tool(
                self._query_tool,
                query_text=f"migration {self.project_name}",
                max_results=20,
            )
            if result:
                return str(result)[:2000]
        except Exception:
            pass
        return ""

    def finalize_migration(self, checkpoint: dict, tasks_json: dict):
        """Записать итоговый отчёт о миграции в Substrate.

        Вызывает equalize_memory для пересчёта band после завершения.
        """
        if not self._enabled:
            return

        s = checkpoint.get("summary", {})
        total = s.get("total", 0)
        completed = s.get("completed", 0)
        pct = (completed / max(total, 1)) * 100

        gate_trigger = f"migration {self.project_name} final"
        session_history = checkpoint.get('session_history', [])
        duration_str = "N/A"
        if session_history:
            first_event = session_history[0]
            duration_str = first_event.get('timestamp', 'unknown')
        payload = (
            f"Migration {self.project_name} complete: {pct:.0f}% ({completed}/{total}). "
            f"Failed: {s.get('failed', 0)}. "
            f"Duration: {duration_str}"
        )

        try:
            from core.core_tools import execute_registered_tool
            execute_registered_tool(
                self._write_tool,
                payload=payload,
                gate_trigger=gate_trigger,
            )
            execute_registered_tool(self._equalize_tool)
        except Exception:
            pass


# ─────────────────────────────────────────────
# MigrationReport — финальный отчёт
# ─────────────────────────────────────────────


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

    reporter = ProgressReporter()
    return reporter.format_report(checkpoint, tasks_json)