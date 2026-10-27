# -*- coding: utf-8 -*-
"""Примеры использования TUI API (консолидировано).

Ранее существовало два перекрывающихся файла (examples_api.py
и integration_example.py). Все уникальные примеры собраны здесь,
дубликаты удалены.
"""

import os
import sys
from typing import Optional, Callable
from datetime import datetime

# Импорт из _core.py (IMMUTABLE)
import importlib.util
_core_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "_core.py")
_spec = importlib.util.spec_from_file_location("_root_core", _core_path)
_root_core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_root_core)

console = _root_core.console


# ═══════════════════════════════════════════════════════════════════════
# Общие утилиты
# ═══════════════════════════════════════════════════════════════════════

class MockMigrationAgent:
    """Mock MigrationAgent для демонстрации интеграции."""

    def __init__(self):
        self.tasks = {}
        self.chat_history = []

    def on_chat_message(self, role: str, content: str):
        """Обработчик новых сообщений чата."""
        console.print(f"[green]\U0001f4e8 Чат: {role}: {content}[/green]")

    def on_task_status_change(self, task_id: str, status: str,
                               name: str = None, progress: float = 0):
        """Обработчик изменения статуса задачи."""
        console.print(
            f"[yellow]\U0001f4cb Задача {task_id}: {status} — "
            f"{name or ''} ({progress:.0f}%)[/yellow]"
        )

    def emit_chat_message(self, role: str, content: str):
        """Эмитит сообщение в чат."""
        console.print(f"[green]\U0001f4e8 [{role}] {content}[/green]")

    def emit_task_status(self, task_id: str, status: str,
                          name=None, progress=0):
        """Эмитит изменение статуса задачи."""
        console.print(
            f"[yellow]\U0001f4cb Задача {task_id}: {status} — "
            f"{name or ''} ({progress:.0f}%)[/yellow]"
        )


def export_chat_to_markdown(app) -> str:
    """Экспорт чата в Markdown."""
    lines = ["# Chat Export", ""]
    for role, content in app.chat_history:
        prefix = (
            "**[User]**" if role == "user"
            else "**[AI]**" if role == "ai"
            else f"**[{role.upper()}]**"
        )
        lines.append(f"{prefix}\n{content}")
        lines.append("")
    return "\n".join(lines)


def _load_shared_context(app):
    """Загрузить shared_context.json в TUIApp, если файл существует."""
    if not os.path.exists("shared_context.json"):
        return
    import json
    with open("shared_context.json", "r", encoding="utf-8") as f:
        ctx = json.load(f)
    console.print(
        "[bold cyan]\U0001f4c2 Загрузка shared_context.json...[/bold cyan]"
    )
    for task_id, data in ctx.get("shared_state", {}).get(
            "sdd_documents", {}).items():
        app.update_task_status(
            task_id,
            "completed" if data.get("iteration", 0) > 1 else "running",
            name=f"SDD для {task_id}",
            progress=100 if data.get("iteration", 0) > 1 else 50,
        )
    for task_id, data in ctx.get("shared_state", {}).get(
            "test_code", {}).items():
        app.add_file(data["file"])


def _load_tasks_json(app):
    """Загрузить задачи из tasks.json, если файл существует."""
    if not os.path.exists("tasks.json"):
        return
    import json
    with open("tasks.json", "r", encoding="utf-8") as f:
        plan = json.load(f)
    console.print(
        "[bold cyan]\U0001f4cb Загрузка задач из tasks.json...[/bold cyan]"
    )
    for task in plan.get("tasks", []):
        app.update_task_status(
            task["id"],
            task.get("status", "pending"),
            name=task.get("target_file", ""),
            progress=(
                0 if task.get("status") == "pending"
                else 100 if task.get("status") == "completed"
                else None
            ),
        )


# ═══════════════════════════════════════════════════════════════════════
# Примеры
# ═══════════════════════════════════════════════════════════════════════

def example_simple_tui():
    """Пример простого TUI с чатом и задачами."""
    from modules.tui.app import TUIApp
    app = TUIApp(width=120, height=30)
    app.add_chat_message(
        "system", "\U0001f916 AUTONOMOUS AI SOFTWARE ENGINEER запущен")
    app.add_chat_message("user", "Привет! Как дела?")
    app.add_chat_message(
        "ai", "Привет! Я готов помочь с миграцией легаси-кода.")
    app.update_task_status(
        "task_1", "running", name="Миграция core.py", progress=25)
    console.print("[bold green]Запуск TUI...[/bold green]")
    app.run()


def example_with_mock_agent():
    """Пример с mock MigrationAgent."""
    from modules.tui.app import TUIApp
    agent = MockMigrationAgent()
    app = TUIApp(width=120, height=30)
    app.on_new_message = agent.on_chat_message
    app.on_task_complete = agent.on_task_status_change
    console.print("[bold green]Запуск TUI с mock agent...[/bold green]")
    app.run()


def example_demo_mode():
    """Пример демо режима без curses."""
    from modules.tui.app import TUIApp
    app = TUIApp(width=120, height=30)
    app.add_chat_message(
        "system", "\U0001f916 AUTONOMOUS AI SOFTWARE ENGINEER запущен")
    app.add_chat_message("user", "Привет!")
    app.add_chat_message("ai", "Привет! Я готов помочь.")
    app.update_task_status(
        "task_1", "running", name="Миграция core.py", progress=50)
    app.update_task_status(
        "task_2", "completed", name="Создание SDD")
    console.print("[bold green]\U0001f3ac Demo режим (без curses)...[/bold green]")
    console.print("[dim]Для запуска в демо режиме используйте demo.py[/dim]")
    console.print(app._build_ui())


def example_async():
    """Пример запуска через asyncio."""
    from modules.tui.app import TUIApp
    app = TUIApp(width=120, height=30)
    console.print("[bold green]\U0001f504 Асинхронный запуск...[/bold green]")
    app.run()


def example_multi_window():
    """Пример мульти-оконного режима."""
    from modules.tui.app import TUIApp
    app1 = TUIApp(width=120, height=30)
    app2 = TUIApp(width=80, height=25)
    app1.add_chat_message("system", "Проект 1")
    app2.add_chat_message("system", "Проект 2")
    console.print(
        "[bold yellow]\u26a0\ufe0f Мульти-оконный режим требует "
        "модификации curses[/bold yellow]")


def example_simple_integration():
    """Пример простой интеграции через shared_context.json."""
    from modules.tui.app import TUIApp
    console.print(
        "[bold green]\U0001f680 Пример: Простая интеграция[/bold green]\n")
    app = TUIApp(width=120, height=30)
    _load_shared_context(app)
    console.print("[bold green]TUI готов к работе![/bold green]")
    console.print("")
    console.print(app._build_ui())
    console.print("")


def example_event_handlers():
    """Пример интеграции с event handlers (имитация выполнения)."""
    from modules.tui.app import TUIApp
    console.print(
        "[bold green]\U0001f680 Пример: Event handlers[/bold green]\n")
    agent = MockMigrationAgent()
    app = TUIApp(width=120, height=30)
    app.on_new_message = lambda role, content: agent.emit_chat_message(
        role, content)
    app.on_task_complete = lambda tid, status, name=None, progress=0: \
        agent.emit_task_status(tid, status, name, progress)

    console.print("[bold cyan]\U0001f3ac Имитация выполнения задач...[/bold cyan]")
    for stage in ["SDD", "TDD", "Coding", "Tests"]:
        agent.emit_chat_message("system", f"\U0001f4d0 {stage}...")
        for pct in [25, 50, 75, 100]:
            app.update_task_status(
                "task_1", "running", name="Миграция core.py", progress=pct)
            import time
            time.sleep(0.3)
        agent.emit_chat_message("ai", f"{stage} завершена!")

    console.print("")
    for i in range(1, 4):
        app.update_task_status(
            f"task_{i}", "completed", name=f"Задача #{i}", progress=100)

    console.print("\n[bold green]TUI завершил работу![/bold green]")
    console.print(app._build_ui())


def example_live_progress():
    """Пример live update с прогрессом задач."""
    from modules.tui.app import TUIApp
    console.print(
        "[bold green]\U0001f680 Пример: Live progress[/bold green]\n")
    app = TUIApp(width=120, height=30)
    app.add_chat_message(
        "system", "\U0001f916 AUTONOMOUS AI SOFTWARE ENGINEER запущен")
    app.add_chat_message("user", "Начни миграцию!")
    app.add_chat_message(
        "ai", "ОК, начинаю анализировать проект...")

    task_id = "task_1"
    name = "Миграция core.py"
    console.print("[bold cyan]\U0001f4ca Live update...[/bold cyan]")
    for progress in [5, 10, 25, 40, 60, 80, 95, 100]:
        app.update_task_status(task_id, "running", name=name, progress=progress)
        import time
        time.sleep(0.2)

    console.print("\n[bold green]Задача завершена![/bold green]")
    app.update_task_status(task_id, "completed", name=name, progress=100)
    console.print(app._build_ui())


def example_with_hot_reload():
    """Пример с hot reload при изменении shared_context.json."""
    from modules.tui.app import TUIApp
    app = TUIApp(width=120, height=30)
    _load_shared_context(app)
    console.print("[bold green]Запуск с hot reload...[/bold green]")
    app.run()


def example_export_chat():
    """Пример экспорта чата."""
    from modules.tui.app import TUIApp
    app = TUIApp(width=120, height=30)
    app.add_chat_message(
        "system", "\U0001f916 AUTONOMOUS AI SOFTWARE ENGINEER запущен")
    app.add_chat_message("user", "Привет!")
    app.add_chat_message("ai", "Привет! Я готов помочь.")
    app.add_chat_message("user", "Как работает TUI?")
    app.add_chat_message(
        "ai", "TUI использует Rich для рендеринга и Curses для input.")
    console.print("[bold cyan]\U0001f4dd Экспорт чата в Markdown:[/bold cyan]")
    console.print(export_chat_to_markdown(app))


def example_multi_task():
    """Пример мульти-задачного режима."""
    from modules.tui.app import TUIApp
    app = TUIApp(width=120, height=30)
    tasks = [
        ("task_1", "running", "Миграция core.py", 25),
        ("task_2", "completed", "Создание SDD", 100),
        ("task_3", "pending", "Написание тестов", 0),
        ("task_4", "failed", "Исправление ошибок", 80),
    ]
    for task_id, status, name, progress in tasks:
        app.update_task_status(
            task_id, status, name=name, progress=progress)
    console.print("[bold cyan]\U0001f4ca Мульти-задачный режим:[/bold cyan]")
    console.print(app._build_ui())


def example_full_demo():
    """Полный демо режим."""
    from modules.tui.app import TUIApp
    console.print("[bold green]\U0001f3ac DEMO MODE: Полный[/bold green]\n")
    app = TUIApp(width=120, height=30)
    app.add_chat_message(
        "system", "\U0001f916 AUTONOMOUS AI SOFTWARE ENGINEER запущен")
    app.add_chat_message("user", "Привет! Как дела?")
    app.add_chat_message(
        "ai", "Привет! Я готов помочь с миграцией легаси-кода.")
    app.update_task_status(
        "task_1", "running", name="Миграция core.py", progress=25)
    app.update_task_status(
        "task_2", "completed", name="Создание SDD")
    app.update_task_status(
        "task_3", "pending", name="Написание тестов")
    app.add_file("core.py")
    app.add_file("agents/migration_agent.py")
    app.add_file("modules/executor.py")
    app.add_file("shared_context.json")
    console.print("[bold cyan]\U0001f4ca UI:[/bold cyan]")
    console.print(app._build_ui())
    console.print("")


# ═══════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════

def main():
    """CLI интерфейс для запуска примеров TUI."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Примеры TUI для Autonomous AI Software Engineer")
    parser.add_argument(
        "--example",
        choices=[
            "simple",       # Простой TUI
            "mock",         # С mock agent
            "demo",         # Демо без curses
            "async",        # Асинхронный
            "multiwin",     # Мульти-оконный
            "simple_int",   # Простая интеграция
            "events",       # Event handlers
            "live",         # Live progress
            "hotreload",    # Hot reload
            "export",       # Экспорт чата
            "multitask",    # Мульти-задачный
            "full_demo",    # Полный демо
        ],
        default="full_demo",
        help="Выбор примера",
    )
    parser.add_argument(
        "--width", type=int, default=120, help="Ширина терминала")
    parser.add_argument(
        "--height", type=int, default=30, help="Высота терминала")

    args = parser.parse_args()

    examples = {
        "simple": example_simple_tui,
        "mock": example_with_mock_agent,
        "demo": example_demo_mode,
        "async": example_async,
        "multiwin": example_multi_window,
        "simple_int": example_simple_integration,
        "events": example_event_handlers,
        "live": example_live_progress,
        "hotreload": example_with_hot_reload,
        "export": example_export_chat,
        "multitask": example_multi_task,
        "full_demo": example_full_demo,
    }

    fn = examples.get(args.example, example_full_demo)
    fn()


if __name__ == "__main__":
    main()
