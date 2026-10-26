# -*- coding: utf-8 -*-
"""Примеры использования TUI API."""

import os
import sys
from typing import Optional, Callable
from datetime import datetime

# Импорт из _core.py (IMMUTABLE)
import importlib.util
_core_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "_core.py")
_spec = importlib.util.spec_from_file_location("_root_core", _core_path)
_root_core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_root_core)

console = _root_core.console


# ─────────────────────────────────────────────
# Пример 1: Простой TUI без интеграции
# ─────────────────────────────────────────────

def example_simple_tui():
    """Пример простого TUI с чатом и задачами."""
    
    from modules.tui.app import TUIApp
    
    app = TUIApp(width=120, height=30)
    
    # Добавляем несколько сообщений в чат
    app.add_chat_message("system", "🤖 AUTONOMOUS AI SOFTWARE ENGINEER запущен")
    app.add_chat_message("user", "Привет! Как дела?")
    app.add_chat_message("ai", "Привет! Я готов помочь с миграцией легаси-кода.")
    
    # Добавляем задачу
    app.update_task_status("task_1", "running", name="Миграция core.py", progress=25)
    
    console.print("[bold green]Запуск TUI...[/bold green]")
    app.run()


# ─────────────────────────────────────────────
# Пример 2: Интеграция с MigrationAgent
# ─────────────────────────────────────────────

class MockMigrationAgent:
    """Mock MigrationAgent для демонстрации интеграции."""
    
    def __init__(self):
        self.tasks = {}
        self.chat_history = []
        
    def on_chat_message(self, role: str, content: str):
        """Обработчик новых сообщений чата."""
        print(f"[green]📨 Чат: {role}: {content}[/green]")
        
    def on_task_status_change(self, task_id: str, status: str, name: str = None, progress: float = 0):
        """Обработчик изменения статуса задачи."""
        print(f"[yellow]📋 Задача {task_id}: {status} — {name or ''} ({progress:.0f}%)[/yellow]")


def example_with_mock_agent():
    """Пример с mock MigrationAgent."""
    
    from modules.tui.app import TUIApp
    
    # Создаём mock agent
    agent = MockMigrationAgent()
    
    # Создаём TUI и привязываем event handlers
    app = TUIApp(width=120, height=30)
    app.on_new_message = agent.on_chat_message
    app.on_task_complete = agent.on_task_status_change
    
    console.print("[bold green]Запуск TUI с mock agent...[/bold green]")
    app.run()


# ─────────────────────────────────────────────
# Пример 3: Полная интеграция с MigrationAgent
# ─────────────────────────────────────────────

def example_full_integration():
    """Пример полной интеграции с MigrationAgent."""
    
    from modules.tui.app import TUIApp
    
    # Инициализация TUI
    app = TUIApp(width=120, height=30)
    
    console.print("[bold green]🚀 Запуск полной интеграции...[/bold green]")
    
    # Здесь можно подключить реальный MigrationAgent:
    # from agents.migration_agent import MigrationAgent
    # agent = MigrationAgent()
    # app.on_new_message = lambda msg: agent.emit_chat_message(msg)
    # app.on_task_complete = lambda tid, status: agent.emit_task_status(tid, status)
    
    app.run()


# ─────────────────────────────────────────────
# Пример 4: Загрузка задач из tasks.json
# ─────────────────────────────────────────────

def example_load_tasks_from_json():
    """Пример загрузки задач из tasks.json."""
    
    from modules.tui.app import TUIApp
    
    app = TUIApp(width=120, height=30)
    
    # Загружаем задачи из tasks.json если есть
    if os.path.exists("tasks.json"):
        import json
        with open("tasks.json", "r", encoding="utf-8") as f:
            plan = json.load(f)
        
        console.print("[bold cyan]📋 Загрузка задач из tasks.json...[/bold cyan]")
        
        for task in plan.get("tasks", []):
            app.update_task_status(
                task["id"],
                task.get("status", "pending"),
                name=task.get("target_file", ""),
                progress=0 if task.get("status") == "pending" else 100 if task.get("status") == "completed" else None
            )
    
    console.print("[bold green]Запуск TUI с задачами...[/bold green]")
    app.run()


# ─────────────────────────────────────────────
# Пример 5: Добавление файлов проекта
# ─────────────────────────────────────────────

def example_with_file_explorer():
    """Пример с отображением файлов проекта."""
    
    from modules.tui.app import TUIApp
    
    app = TUIApp(width=120, height=30)
    
    # Добавляем файлы проекта
    app.add_file("core.py")
    app.add_file("agents/migration_agent.py")
    app.add_file("modules/executor.py")
    app.add_file("shared_context.json")
    
    console.print("[bold green]Запуск TUI с файлами...[/bold green]")
    app.run()


# ─────────────────────────────────────────────
# Пример 6: Demo режим (без curses, только rich)
# ─────────────────────────────────────────────

def example_demo_mode():
    """Пример демо режима без curses."""
    
    from modules.tui.app import TUIApp
    
    app = TUIApp(width=120, height=30)
    
    # Добавляем тестовые данные
    app.add_chat_message("system", "🤖 AUTONOMOUS AI SOFTWARE ENGINEER запущен")
    app.add_chat_message("user", "Привет!")
    app.add_chat_message("ai", "Привет! Я готов помочь.")
    
    app.update_task_status("task_1", "running", name="Миграция core.py", progress=50)
    app.update_task_status("task_2", "completed", name="Создание SDD")
    
    console.print("[bold green]🎬 Demo режим (без curses)...[/bold green]")
    console.print("[dim]Для запуска в демо режиме используйте demo.py[/dim]")
    
    # В демо режиме можно просто показать UI один раз:
    console.print(app._build_ui())


# ─────────────────────────────────────────────
# Пример 7: Использование с asyncio
# ─────────────────────────────────────────────

async def example_async():
    """Пример запуска через asyncio."""
    
    from modules.tui.app import TUIApp
    
    app = TUIApp(width=120, height=30)
    
    console.print("[bold green]🔄 Асинхронный запуск...[/bold green]")
    
    # Здесь можно запустить agent в фоне:
    # asyncio.create_task(run_migration_agent())
    
    app.run()


# ─────────────────────────────────────────────
# Пример 8: Hot reload при изменении shared_context.json
# ─────────────────────────────────────────────

def example_with_hot_reload():
    """Пример с hot reload."""
    
    from modules.tui.app import TUIApp
    
    app = TUIApp(width=120, height=30)
    
    # Загружаем shared_context.json если есть
    if os.path.exists("shared_context.json"):
        import json
        with open("shared_context.json", "r", encoding="utf-8") as f:
            ctx = json.load(f)
        
        console.print("[bold cyan]🔄 Hot reload: загружен shared_context.json[/bold cyan]")
        
        # Восстанавливаем задачи из shared context
        for task_id, data in ctx.get("shared_state", {}).get("sdd_documents", {}).items():
            app.update_task_status(
                task_id,
                "completed" if data.get("iteration", 0) > 1 else "running",
                name=f"SDD для {task_id}",
                progress=100 if data.get("iteration", 0) > 1 else 50
            )
    
    console.print("[bold green]Запуск с hot reload...[/bold green]")
    app.run()


# ─────────────────────────────────────────────
# Пример 9: Мульти-оконный режим (несколько TUI инстансов)
# ─────────────────────────────────────────────

def example_multi_window():
    """Пример мульти-оконного режима."""
    
    from modules.tui.app import TUIApp
    
    # Создаём несколько TUI инстансов для разных проектов
    app1 = TUIApp(width=120, height=30)
    app2 = TUIApp(width=80, height=25)
    
    # Наполняем данными
    app1.add_chat_message("system", "Проект 1")
    app2.add_chat_message("system", "Проект 2")
    
    console.print("[bold yellow]⚠️ Мульти-оконный режим требует модификации curses[/bold yellow]")
    console.print("[dim]Для реализации нужно использовать multiple stdscr или ncurses wrapper[/dim]")


# ─────────────────────────────────────────────
# Пример 10: Экспорт чата в Markdown
# ─────────────────────────────────────────────

def export_chat_to_markdown(app):
    """Экспорт чата в Markdown."""
    
    lines = ["# Chat Export", ""]
    
    for role, content in app.chat_history:
        prefix = "**[User]**" if role == "user" else \
                "**[AI]**" if role == "ai" else f"**[{role.upper()}]**"
        lines.append(f"{prefix}\n{content}")
        lines.append("")
    
    return "\n".join(lines)


def example_export_chat():
    """Пример экспорта чата."""
    
    from modules.tui.app import TUIApp
    
    app = TUIApp(width=120, height=30)
    
    # Добавляем сообщения
    app.add_chat_message("system", "🤖 AUTONOMOUS AI SOFTWARE ENGINEER запущен")
    app.add_chat_message("user", "Привет!")
    app.add_chat_message("ai", "Привет! Я готов помочь.")
    
    markdown = export_chat_to_markdown(app)
    
    console.print("[bold green]📝 Экспорт чата в Markdown:[/bold green]")
    console.print(markdown)


# ─────────────────────────────────────────────
# Пример 11: Использование с MigrationAgent (реальный код)
# ─────────────────────────────────────────────

def example_with_real_migration_agent():
    """Пример интеграции с реальным MigrationAgent."""
    
    from modules.tui.app import TUIApp
    
    # Инициализация TUI
    app = TUIApp(width=120, height=30)
    
    console.print("[bold green]🚀 Интеграция с MigrationAgent...[/bold green]")
    
    try:
        from agents.migration_agent import MigrationAgent
        
        # Создаём agent
        agent = MigrationAgent()
        
        # Привязываем event handlers
        app.on_new_message = lambda msg: console.print(f"[green]📨 {msg}[/green]")
        app.on_task_complete = lambda tid, status: console.print(
            f"[yellow]📋 Задача {tid}: {status}[/yellow]"
        )
        
        # Можно также читать shared_context.json для обновления UI
        if os.path.exists("shared_context.json"):
            import json
            with open("shared_context.json", "r", encoding="utf-8") as f:
                ctx = json.load(f)
            
            for task_id, data in ctx.get("shared_state", {}).get(
                "sdd_documents", {}
            ).items():
                app.update_task_status(
                    task_id,
                    "completed" if data.get("iteration", 0) > 1 else "running",
                    name=f"SDD для {task_id}",
                    progress=100 if data.get("iteration", 0) > 1 else 50
                )
        
        console.print("[bold green]TUI готов к работе с MigrationAgent![/bold green]")
        
    except ImportError:
        console.print("[yellow]⚠️ MigrationAgent не найден. Запуск в демо режиме.[/yellow]")
    
    app.run()


# ─────────────────────────────────────────────
# Пример 12: Использование через CLI
# ─────────────────────────────────────────────

def main():
    """CLI интерфейс для запуска TUI."""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="TUI для Autonomous AI Software Engineer")
    parser.add_argument(
        "--mode", 
        choices=["simple", "demo", "integration"],
        default="simple",
        help="Режим работы"
    )
    parser.add_argument(
        "--width",
        type=int,
        default=120,
        help="Ширина терминала"
    )
    parser.add_argument(
        "--height",
        type=int,
        default=30,
        help="Высота терминала"
    )
    
    args = parser.parse_args()
    
    if args.mode == "simple":
        example_simple_tui()
    elif args.mode == "demo":
        example_demo_mode()
    elif args.mode == "integration":
        example_with_real_migration_agent()


if __name__ == "__main__":
    main()
