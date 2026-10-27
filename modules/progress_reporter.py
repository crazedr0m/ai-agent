# -*- coding: utf-8 -*-
# modules/progress_reporter.py — Отчёты о прогрессе миграции


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

                if status == "completed" and task_info.get("details", {}).get("duration_seconds"):
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