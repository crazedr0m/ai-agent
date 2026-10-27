# -*- coding: utf-8 -*-
# modules/log16_integration.py — Интеграция с LOG16 Substrate (Фаза 6.4)


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
            строка с фактами о проекте (для LLM)
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