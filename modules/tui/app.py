# -*- coding: utf-8 -*-
"""TUIApp — основной класс приложения с event loop (Фаза 2)."""

import os
import sys
import json
from typing import Optional, Callable
from datetime import datetime
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich import box
import curses

from .components import get_file_icon


class TUIApp:
    """TUI Application — основной класс приложения.

    Фаза 2: поддержка интеграции с CasualAgent, сессии, трейсинг.
    """

    HOTKEYS = {
        "q": ("quit", "Выход из приложения"),
        "n": ("new_task", "Новая задача"),
        "c": ("chat", "Отправить сообщение в чат"),
        "t": ("toggle_tasks", "Показать/скрыть задачи"),
        "f": ("toggle_files", "Показать/скрыть файлы"),
        "u": ("update", "Обновить статус"),
        "h": ("help", "Помощь"),
        "s": ("save_session", "Сохранить сессию"),
    }

    def __init__(self, width: int = 120, height: int = 30):
        self.width = width
        self.height = height
        self.console = Console()

        # Чат история
        self.chat_history: list[tuple[str, str]] = []

        # Задачи (tasks)
        self.tasks: dict[str, dict] = {}
        self.task_counter = 0

        # Файлы проекта
        self.project_files: list[dict] = []

        # Статусы
        self.status_messages: list[tuple[str, str]] = []
        self.current_task_id: Optional[str] = None

        # Event handlers
        self.on_new_message: Optional[Callable] = None
        self.on_task_complete: Optional[Callable] = None

        # UI visibility
        self.show_tasks = True
        self.show_files = True

        # Фаза 2: ссылка на агента и трейсер
        self._agent = None
        self._tracer = None
        self._session_id = None

    def run(self, agent=None, tracer=None):
        """Запуск event loop с curses.

        Args:
            agent: экземпляр CasualAgent для обработки сообщений
            tracer: экземпляр TraceSession для трейсинга
        """
        self._agent = agent
        self._tracer = tracer

        if self._tracer:
            self._session_id = self._tracer.session_id

        try:
            self.stdscr = curses.initscr()
            curses.curs_set(0)
            self.stdscr.timeout(100)

            with Live(self._render(), console=self.console, refresh_per_second=10) as live:
                while True:
                    key = self.stdscr.getch()

                    if key == -1 or key == ord('q'):
                        break

                    try:
                        action, description = self.HOTKEYS.get(chr(key).lower(), (None, None))
                    except (ValueError, KeyError):
                        action = None

                    if action:
                        core_func = getattr(self, f"_on_{action}", None)
                        if core_func:
                            core_func()

        except KeyboardInterrupt:
            pass
        finally:
            curses.endwin()
            if self._tracer:
                self._tracer.close()

    def _render(self):
        """Рендеринг UI."""
        chat_content = self._render_chat()

        tasks_panel_str = ""
        if self.show_tasks and self.tasks:
            tasks_lines = []
            for task_id, task in sorted(self.tasks.items()):
                status_icon = {
                    "pending": "[yellow]⏳[/yellow]",
                    "running": "[bold green]▶️[/bold green]",
                    "completed": "[green]✅[/green]",
                    "failed": "[red]❌[/red]",
                    "retrying": "[orange]🔄[/orange]",
                }.get(task.get("status", "pending"), "[?]")
                tasks_lines.append(f"{task_id}: {status_icon} {task.get('name', 'Unnamed task')}")
            if tasks_lines:
                tasks_panel_str = "\n".join(tasks_lines)

        files_panel_str = ""
        if self.show_files and self.project_files:
            folders = {}
            for f in self.project_files:
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
                    files_lines.append(f"  ... и ещё {len(files_list) - 10} файлов")
            if files_lines:
                files_panel_str = "\n".join(files_lines)

        status_bar = self._render_status()

        output_parts = [chat_content]
        if tasks_panel_str:
            output_parts.append(f"[bold yellow]📋 ЗАДАЧИ[/bold yellow]\n{tasks_panel_str}")
        if files_panel_str:
            output_parts.append(f"[bold cyan]📁 ФАЙЛЫ[/bold cyan]\n{files_panel_str}")

        # Фаза 2: показываем ID сессии
        session_info = ""
        if self._session_id:
            session_info = f"\n[dim]Сессия: {self._session_id}[/dim]"

        return Panel(
            "\n".join(output_parts) + session_info,
            title="[bold blue]🤖 AUTONOMOUS AI SOFTWARE ENGINEER[/bold blue]",
            border_style="blue",
            box=box.ROUNDED,
        )

    def _build_ui(self):
        """Alias for _render() — сохранение обратной совместимости."""
        return self._render()

    def _render_chat(self):
        """Рендеринг чата."""
        if not self.chat_history:
            return "[dim]Чат пуст. Нажмите [cyan]'c'[/cyan] для отправки сообщения.[/dim]"

        lines = []
        for msg in reversed(self.chat_history[-50:]):
            role, content = msg
            if role == "user":
                prefix = "[green][bold]>[/bold][/green] Пользователь"
            elif role == "ai":
                prefix = "[red][bold]<[/bold][/red] AI-Агент"
            else:
                prefix = "[dim]⚙️ Система[/dim]"
            lines.append(f"{prefix}\n{content}")

        return "\n\n".join(lines)

    def _render_status(self):
        """Рендеринг статус бара."""
        total = len([t for t in self.tasks.values() if t.get("status") != "completed"])
        completed = len([t for t in self.tasks.values() if t.get("status") == "completed"])

        status_lines = [
            f"[dim]Задачи: {total} в работе, {completed} завершено[/dim]",
            f"[dim]Чат: {len(self.chat_history)} сообщений[/dim]",
        ]

        for timestamp, message in self.status_messages[-3:]:
            status_lines.append(f"[dim]{timestamp}: {message}[/dim]")

        return "\n".join(status_lines)

    def _on_quit(self):
        """Обработчик выхода."""
        if self._tracer:
            self._tracer.close()
        print("\nВыход из приложения...")
        sys.exit(0)

    def _on_new_task(self):
        """Создание новой задачи."""
        self.task_counter += 1
        task_id = f"task_{self.task_counter}"

        self.tasks[task_id] = {
            "id": task_id,
            "name": f"Новая задача #{self.task_counter}",
            "status": "pending",
            "progress": 0,
        }

    def _on_chat(self):
        """Отправка сообщения в чат и обработка через агента."""
        stdscr = self.stdscr
        curses.curs_set(1)

        try:
            height, width = stdscr.getmaxyx()
            input_height = min(4, (height - 3) // 2)

            prompt = "Сообщение: "
            stdscr.addstr(height - input_height - 1, 0, prompt.ljust(width))
            stdscr.refresh()

            msg_bytes = []
            while True:
                key = stdscr.getch()

                if key == curses.KEY_ENTER or key in [10, 13]:
                    break

                elif key == 27:
                    msg = "".join(msg_bytes)
                    self.console.print(f"[yellow]Отменено: '{msg}'[/yellow]")
                    return

                elif key == curses.KEY_BACKSPACE or key == 127 or key == 8:
                    if msg_bytes:
                        msg_bytes.pop()
                        stdscr.move(height - input_height, 0)
                        stdscr.clrtoe()
                        prompt = "Сообщение: "
                        stdscr.addstr(height - input_height - 1, 0, prompt.ljust(width))
                        stdscr.refresh()

                elif key >= 32 and key < 127:
                    msg_bytes.append(chr(key))
                    cursor_x = stdscr.getyx()[1]
                    stdscr.addch(height - input_height, cursor_x, chr(key))
                    stdscr.refresh()

            message = "".join(msg_bytes)
            if not message.strip():
                return

        finally:
            curses.curs_set(0)

        # Добавляем сообщение пользователя в чат
        self.chat_history.append(("user", message))

        # Фаза 2: если есть агент — обрабатываем через него
        if self._agent:
            self.status_messages.insert(0, (datetime.now().strftime("%H:%M"), "🤔 Агент думает..."))

            # Временно выходим из curses для вывода агента
            curses.endwin()

            try:
                result = self._agent.run_interactive(
                    message,
                    on_message=self.add_chat_message
                )
            except Exception as e:
                self.add_chat_message("system", f"❌ Ошибка: {e}")
            finally:
                # Возвращаем curses
                self.stdscr = curses.initscr()
                curses.curs_set(0)
                self.stdscr.timeout(100)

            self.status_messages.insert(0, (datetime.now().strftime("%H:%M"), "✅ Ответ получен"))
        else:
            # Без агента — просто echo
            self.chat_history.append(("ai", f"Эхо: {message}"))

    def _on_toggle_tasks(self):
        """Переключение видимости задач."""
        self.show_tasks = not self.show_tasks

    def _on_toggle_files(self):
        """Переключение видимости файлов."""
        self.show_files = not self.show_files

    def _on_update(self):
        """Обновление статуса."""
        self.status_messages.insert(0, (datetime.now().strftime("%H:%M"), "Статус обновлён"))

    def _on_help(self):
        """Отображение помощи."""
        help_text = [
            "[bold cyan]Горячие клавиши:[/bold cyan]",
            "",
            "  q — Выход",
            "  n — Новая задача",
            "  c — Отправить сообщение в чат",
            "  t — Показать/скрыть задачи",
            "  f — Показать/скрыть файлы",
            "  u — Обновить статус",
            "  s — Сохранить сессию",
            "  h — Эта помощь",
        ]

        self.console.print("\n".join(help_text))

    def _on_save_session(self):
        """Сохранить сессию (2.4)."""
        if not self._session_id:
            self.status_messages.insert(0, (datetime.now().strftime("%H:%M"), "⚠️ Нет активной сессии"))
            return

        # Сохраняем историю чата в JSON
        session_data = {
            "session_id": self._session_id,
            "timestamp": datetime.now().isoformat(),
            "chat_history": self.chat_history[-100:],
            "tasks": {k: v for k, v in self.tasks.items()},
        }

        session_file = f"session_{self._session_id}.json"
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)

        self.status_messages.insert(0,
            (datetime.now().strftime("%H:%M"), f"💾 Сессия сохранена: {session_file}"))

    def add_chat_message(self, role: str, content: str):
        """Добавить сообщение в чат."""
        self.chat_history.append((role, content))

    def update_task_status(self, task_id: str, status: str, name: str = None, progress: float = 0):
        """Обновить статус задачи."""
        if task_id not in self.tasks:
            self.task_counter += 1
            task_id = f"task_{self.task_counter}"
            self.tasks[task_id] = {
                "id": task_id,
                "name": name or f"Задача #{self.task_counter}",
                "status": status,
                "progress": progress,
            }
        else:
            self.tasks[task_id]["status"] = status
            if name:
                self.tasks[task_id]["name"] = name
            if progress is not None:
                self.tasks[task_id]["progress"] = progress

    def add_file(self, path: str):
        """Добавить файл проекта."""
        self.project_files.append({
            "path": path,
            "timestamp": datetime.now().isoformat(),
        })
