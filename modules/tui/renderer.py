# -*- coding: utf-8 -*-
"""Renderer — выделенный рендеринг UI для TUIApp."""

import os

from rich.panel import Panel
from rich import box

from .components import get_file_icon


class Renderer:
    """Рендеринг UI-компонентов TUIApp.

    Не владеет состоянием — все данные приходят через параметры render().
    """

    def render(self, chat_history, tasks, project_files,
               status_messages, show_tasks=True, show_files=True,
               session_id=None):
        """Собрать Panel с чатом, задачами, файлами и статусом."""
        chat_content = self._render_chat(chat_history)

        tasks_panel_str = ""
        if show_tasks and tasks:
            tasks_lines = []
            for task_id, task in sorted(tasks.items()):
                status_icon = {
                    "pending": "[yellow]\u23f3[/yellow]",
                    "running": "[bold green]\u25b6[/bold green]",
                    "completed": "[green]\u2705[/green]",
                    "failed": "[red]\u274c[/red]",
                    "retrying": "[orange]\U0001f504[/orange]",
                }.get(task.get("status", "pending"), "[?]")
                tasks_lines.append(
                    f"{task_id}: {status_icon} {task.get('name', 'Unnamed task')}"
                )
            if tasks_lines:
                tasks_panel_str = "\n".join(tasks_lines)

        files_panel_str = ""
        if show_files and project_files:
            folders = {}
            for f in project_files:
                path = f.get("path", "")
                name = os.path.basename(path)
                folder = os.path.dirname(path).split(os.sep)[-1] or "root"
                if folder not in folders:
                    folders[folder] = []
                folders[folder].append(name)

            files_lines = []
            for folder, files_list in sorted(folders.items()):
                files_lines.append(f"[cyan]{folder}[/cyan]:")
                for f_name in files_list[:10]:
                    icon = get_file_icon(f_name)
                    files_lines.append(f"  {icon} {f_name}")
                if len(files_list) > 10:
                    files_lines.append(
                        f"  ... \u0438 \u0435\u0449\u0451 {len(files_list) - 10} \u0444\u0430\u0439\u043b\u043e\u0432"
                    )
            if files_lines:
                files_panel_str = "\n".join(files_lines)

        status_bar = self._render_status(status_messages, tasks, chat_history)

        output_parts = [chat_content]
        if tasks_panel_str:
            output_parts.append(
                f"[bold yellow]\U0001f4cb \u0417\u0410\u0414\u0410\u0427\u0418[/bold yellow]\n{tasks_panel_str}"
            )
        if files_panel_str:
            output_parts.append(
                f"[bold cyan]\U0001f4c1 \u0424\u0410\u0419\u041b\u042b[/bold cyan]\n{files_panel_str}"
            )

        session_info = ""
        if session_id:
            session_info = f"\n[dim]\u0421\u0435\u0441\u0441\u0438\u044f: {session_id}[/dim]"

        return Panel(
            "\n".join(output_parts) + session_info,
            title="[bold blue]\U0001f916 AUTONOMOUS AI SOFTWARE ENGINEER[/bold blue]",
            border_style="blue",
            box=box.ROUNDED,
        )

    def build_ui(self, chat_history, tasks, project_files,
                 status_messages, show_tasks=True, show_files=True,
                 session_id=None):
        """Alias for render() — обратная совместимость."""
        return self.render(chat_history, tasks, project_files,
                           status_messages, show_tasks, show_files, session_id)

    def _render_chat(self, chat_history):
        """Рендеринг чата."""
        if not chat_history:
            return "[dim]Чат пуст. Нажмите [cyan]'c'[/cyan] для отправки сообщения.[/dim]"

        lines = []
        for msg in reversed(chat_history[-50:]):
            role, content = msg
            if role == "user":
                prefix = "[green][bold]>[/bold][/green] Пользователь"
            elif role == "ai":
                prefix = "[red][bold]<[/bold][/red] AI-Агент"
            else:
                prefix = "[dim]\u2699 Система[/dim]"
            lines.append(f"{prefix}\n{content}")

        return "\n\n".join(lines)

    def _render_status(self, status_messages, tasks, chat_history):
        """Рендеринг статус бара."""
        total = len([t for t in tasks.values() if t.get("status") != "completed"])
        completed = len([t for t in tasks.values() if t.get("status") == "completed"])

        status_lines = [
            f"[dim]Задачи: {total} в работе, {completed} завершено[/dim]",
            f"[dim]Чат: {len(chat_history)} сообщений[/dim]",
        ]

        for timestamp, message in status_messages[-3:]:
            status_lines.append(f"[dim]{timestamp}: {message}[/dim]")

        return "\n".join(status_lines)