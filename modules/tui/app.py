# -*- coding: utf-8 -*-
"""TUIApp — основной класс приложения с event loop (Фаза 2).

Рендеринг делегирован Renderer (modules/tui/renderer.py).
В этом файле: состояние, event loop, обработчики.
"""

import os
import sys
import json
import select
import termios
import tty
from typing import Optional, Callable
from datetime import datetime

from rich.console import Console
from rich.cells import cell_len

from .renderer import Renderer


def _read_key(fd: int, timeout: float = 0.2):
    """Неблокирующее чтение одного символа с fd (cbreak-режим)."""
    ready, _, _ = select.select([fd], [], [], timeout)
    if not ready:
        return None
    try:
        data = os.read(fd, 1)
    except OSError:
        return None
    if not data:
        return None
    return data.decode("utf-8", "replace")


class TUIApp:
    """TUI Application — основной класс приложения.

    Фаза 2: поддержка интеграции с CasualAgent, сессии, трейсинг.
    Рендеринг через Renderer.
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
        self.renderer = Renderer()

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
        self._fd = None
        self._dirty = True

    def run(self, agent=None, tracer=None):
        """Запуск event loop.

        Args:
            agent: экземпляр CasualAgent для обработки сообщений
            tracer: экземпляр TraceSession для трейсинга
        """
        self._agent = agent
        self._tracer = tracer

        if self._tracer:
            self._session_id = self._tracer.session_id

        if not sys.stdin.isatty():
            self._run_console()
            return

        fd = sys.stdin.fileno()
        self._fd = fd
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            while True:
                if self._dirty:
                    self._draw()
                    self._dirty = False
                key = _read_key(fd, 0.2)
                if key is None:
                    continue
                if key in ("q", "Q"):
                    break

                action, _ = self.HOTKEYS.get(key.lower(), (None, None))
                if not action or action == "quit":
                    continue

                handler = getattr(self, f"_on_{action}", None)
                if handler:
                    handler()
                    self._dirty = True

        except KeyboardInterrupt:
            pass
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            self.console.clear()
            if self._tracer:
                self._tracer.close()

    def _read_line(self, prompt: str):
        """Прочитать строку посимвольно в cbreak-режиме. None при отмене."""
        if getattr(self, "_fd", None) is None:
            try:
                return self.console.input(f"[bold green]{prompt}[/bold green]")
            except (EOFError, KeyboardInterrupt):
                return None
        sys.stdout.write(prompt)
        sys.stdout.flush()
        buf = []
        pending = bytearray()
        while True:
            ready, _, _ = select.select([self._fd], [], [], None)
            if not ready:
                continue
            try:
                raw = os.read(self._fd, 1)
            except OSError:
                return None
            if not raw:
                return None
            b = raw[0]
            if b in (0x0d, 0x0a):
                sys.stdout.write("\n")
                sys.stdout.flush()
                break
            if b == 0x03:
                raise KeyboardInterrupt
            if b == 0x1b:
                sys.stdout.write("\n")
                sys.stdout.flush()
                return None
            if b in (0x7f, 0x08):
                if buf:
                    removed = buf.pop()
                    width = max(1, cell_len(removed))
                    sys.stdout.write("\b \b" * width)
                    sys.stdout.flush()
                continue
            pending.append(b)
            try:
                ch = pending.decode("utf-8")
            except UnicodeDecodeError as exc:
                if exc.reason == "unexpected end of data":
                    continue
                ch = pending.decode("utf-8", "replace")
            pending.clear()
            buf.append(ch)
            sys.stdout.write(ch)
            sys.stdout.flush()
        return "".join(buf)

    def _draw(self):
        """Отрисовать панель и строку подсказки.

        Перезапись на месте (курсор в начало + очистка до конца экрана)
        вместо полной очистки — устраняет мерцание.
        """
        sys.stdout.write("\x1b[H")
        self.console.print(self._render())
        self.console.print(self._hint())
        sys.stdout.write("\x1b[J")
        sys.stdout.flush()

    def _hint(self):
        """Строка подсказки по горячим клавишам."""
        return ("[dim]c — чат · n — задача · t — задачи · f — файлы · "
                "u — обновить · h — помощь · s — сохранить · q — выход[/dim]")

    def _run_console(self):
        """Консольный режим без TTY (fallback)."""
        try:
            while True:
                self.console.clear()
                self.console.print(self._render())
                self.console.print(self._hint())
                try:
                    key = self.console.input(
                        "[bold cyan]Команда: [/bold cyan]").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    break

                if key in ("q", "quit", "exit"):
                    break
                if not key:
                    continue

                action, _ = self.HOTKEYS.get(key, (None, None))
                if not action or action == "quit":
                    continue

                handler = getattr(self, f"_on_{action}", None)
                if handler:
                    handler()
        finally:
            if self._tracer:
                self._tracer.close()

    def _render(self):
        """Делегирует рендеринг Renderer."""
        return self.renderer.render(
            chat_history=self.chat_history,
            tasks=self.tasks,
            project_files=self.project_files,
            status_messages=self.status_messages,
            show_tasks=self.show_tasks,
            show_files=self.show_files,
            session_id=self._session_id,
        )

    def _build_ui(self):
        """Alias for _render() — обратная совместимость."""
        return self._render()

    # ─── Обработчики событий ───────────────────────────────────────────

    def _on_quit(self):
        """Выход."""
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
        try:
            message = self._read_line("Сообщение: ")
        except (EOFError, KeyboardInterrupt):
            return

        if message is None or not message.strip():
            return

        self.chat_history.append(("user", message))

        if self._agent:
            self.status_messages.insert(
                0, (datetime.now().strftime("%H:%M"),
                    "\U0001f914 Агент думает..."))
            try:
                self._agent.run_interactive(
                    message,
                    on_message=self.add_chat_message
                )
            except Exception as e:
                self.add_chat_message("system", f"\u274c Ошибка: {e}")
            self.status_messages.insert(
                0, (datetime.now().strftime("%H:%M"),
                    "\u2705 Ответ получен"))
        else:
            self.chat_history.append(("ai", f"Эхо: {message}"))

    def _on_toggle_tasks(self):
        """Переключение видимости задач."""
        self.show_tasks = not self.show_tasks

    def _on_toggle_files(self):
        """Переключение видимости файлов."""
        self.show_files = not self.show_files

    def _on_update(self):
        """Обновление статуса."""
        self.status_messages.insert(
            0, (datetime.now().strftime("%H:%M"), "Статус обновлён"))

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
        self.console.clear()
        self.console.print("\n".join(help_text))
        try:
            self._read_line("Нажмите Enter для возврата... ")
        except (EOFError, KeyboardInterrupt):
            pass

    def _on_save_session(self):
        """Сохранить сессию (2.4)."""
        if not self._session_id:
            self.status_messages.insert(
                0, (datetime.now().strftime("%H:%M"),
                    "\u26a0\ufe0f Нет активной сессии"))
            return

        session_data = {
            "session_id": self._session_id,
            "timestamp": datetime.now().isoformat(),
            "chat_history": self.chat_history[-100:],
            "tasks": {k: v for k, v in self.tasks.items()},
        }

        session_file = f"session_{self._session_id}.json"
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)

        self.status_messages.insert(
            0, (datetime.now().strftime("%H:%M"),
                f"\U0001f4be Сессия сохранена: {session_file}"))

    # ─── Публичные методы для агента ───────────────────────────────────

    def add_chat_message(self, role: str, content: str):
        """Добавить сообщение в чат."""
        self.chat_history.append((role, content))

    def update_task_status(self, task_id: str, status: str,
                           name: str = None, progress: float = 0):
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
