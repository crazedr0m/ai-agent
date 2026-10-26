# -*- coding: utf-8 -*-
"""Пример полной интеграции TUI с MigrationAgent."""

import os
import sys
from datetime import datetime
import json

# Импорт из _core.py (IMMUTABLE)
import importlib.util
_core_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "_core.py")
_spec = importlib.util.spec_from_file_location("_root_core", _core_path)
_root_core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_root_core)

console = _root_core.console


# ─────────────────────────────────────────────
# Пример 1: Простая интеграция через shared_context.json
# ─────────────────────────────────────────────

def example_simple_integration():
    """Пример простой интеграции через shared_context.json."""
    
    from modules.tui.app import TUIApp
    
    console.print("[bold green]🚀 Пример 1: Простая интеграция[/bold green]\n")
    
    # Создаём TUI
    app = TUIApp(width=120, height=30)
    
    # Загружаем shared_context.json для обновления UI
    if os.path.exists("shared_context.json"):
        with open("shared_context.json", "r", encoding="utf-8") as f:
            ctx = json.load(f)
        
        console.print("[bold cyan]📂 Загрузка shared_context.json...[/bold cyan]")
        
        # Восстанавливаем задачи из SDD documents
        for task_id, data in ctx.get("shared_state", {}).get(
            "sdd_documents", {}
        ).items():
            app.update_task_status(
                task_id,
                "completed" if data.get("iteration", 0) > 1 else "running",
                name=f"SDD для {task_id}",
                progress=100 if data.get("iteration", 0) > 1 else 50
            )
        
        # Добавляем файлы из shared context
        for task_id, data in ctx.get("shared_state", {}).get(
            "test_code", {}
        ).items():
            app.add_file(data["file"])
    
    console.print("[bold green]TUI готов к работе![/bold green]")
    console.print("")
    console.print(app._build_ui())
    console.print("")


# ─────────────────────────────────────────────
# Пример 2: Интеграция с event handlers (mock agent)
# ─────────────────────────────────────────────

class MockMigrationAgent:
    """Mock MigrationAgent для демонстрации интеграции."""
    
    def __init__(self):
        self.tasks = {}
        self.chat_history = []
        
    def emit_chat_message(self, role: str, content: str):
        """Эмитит сообщение в чат."""
        console.print(f"[green]📨 [{role}] {content}[/green]")
    
    def emit_task_status(self, task_id: str, status: str, name=None, progress=0):
        """Эмитит изменение статуса задачи."""
        console.print(
            f"[yellow]📋 Задача {task_id}: {status} — {name or ''} ({progress:.0f}%)[/yellow]"
        )


def example_event_handlers():
    """Пример интеграции с event handlers."""
    
    from modules.tui.app import TUIApp
    
    console.print("[bold green]🚀 Пример 2: Интеграция с event handlers[/bold green]\n")
    
    # Создаём mock agent
    agent = MockMigrationAgent()
    
    # Создаём TUI и привязываем event handlers
    app = TUIApp(width=120, height=30)
    app.on_new_message = lambda role, content: agent.emit_chat_message(role, content)
    app.on_task_complete = lambda tid, status, name=None, progress=0: \
        agent.emit_task_status(tid, status, name, progress)
    
    # Имитируем выполнение задач
    console.print("[bold cyan]🎬 Имитация выполнения задач...[/bold cyan]")
    
    # Задача 1: SDD → TDD → Coding → Tests → Critic
    for stage in ["SDD", "TDD", "Coding", "Tests"]:
        agent.emit_chat_message("system", f"📐 {stage}...")
        
        # Имитация прогресса
        for progress in [25, 50, 75, 100]:
            app.update_task_status(
                "task_1",
                "running",
                name="Миграция core.py",
                progress=progress
            )
            
            # Имитация задержки
            import time
            time.sleep(0.3)
        
        agent.emit_chat_message("ai", f"{stage} завершена!")
    
    # Задача 2: параллельное выполнение
    console.print("")
    console.print("[bold cyan]🎬 Параллельное выполнение задач...[/bold cyan]")
    
    for i in range(1, 4):
        app.update_task_status(
            f"task_{i}",
            "completed",
            name=f"Задача #{i}",
            progress=100
        )
    
    console.print("")
    console.print("[bold green]TUI завершил работу![/bold green]")
    console.print(app._build_ui())


# ─────────────────────────────────────────────
# Пример 3: Интеграция с реальным MigrationAgent
# ─────────────────────────────────────────────

def example_full_integration():
    """Пример полной интеграции с реальным MigrationAgent."""
    
    from modules.tui.app import TUIApp
    
    console.print("[bold green]🚀 Пример 3: Полная интеграция[/bold green]\n")
    
    try:
        from agents.migration_agent import MigrationAgent
        
        # Создаём agent и TUI
        agent = MigrationAgent()
        app = TUIApp(width=120, height=30)
        
        console.print("[bold cyan]🔌 Привязываем event handlers...[/bold cyan]")
        
        # Привязываем event handlers
        def on_message(role, content):
            console.print(f"[green]📨 [{role}] {content}[/green]")
        
        def on_task(tid, status, name=None, progress=0):
            console.print(
                f"[yellow]📋 Задача {tid}: {status} — {name or ''} ({progress:.0f}%)[/yellow]"
            )
        
        app.on_new_message = on_message
        app.on_task_complete = on_task
        
        # Загружаем shared_context.json для обновления UI
        if os.path.exists("shared_context.json"):
            with open("shared_context.json", "r") as f:
                ctx = json.load(f)
            
            console.print("[bold cyan]📂 Загрузка shared_context.json...[/bold cyan]")
            
            # Восстанавливаем задачи из SDD documents
            for task_id, data in ctx.get("shared_state", {}).get(
                "sdd_documents", {}
            ).items():
                app.update_task_status(
                    task_id,
                    "completed" if data.get("iteration", 0) > 1 else "running",
                    name=f"SDD для {task_id}",
                    progress=100 if data.get("iteration", 0) > 1 else 50
                )
            
            # Добавляем файлы из shared context
            for task_id, data in ctx.get("shared_state", {}).get(
                "test_code", {}
            ).items():
                app.add_file(data["file"])
        
        console.print("[bold green]TUI готов к работе с MigrationAgent![/bold green]")
        console.print("")
        console.print(app._build_ui())
        console.print("")
        
    except ImportError:
        console.print("[yellow]⚠️ MigrationAgent не найден. Запуск в демо режиме.[/yellow]")


# ─────────────────────────────────────────────
# Пример 4: Live update с прогрессом задач
# ─────────────────────────────────────────────

def example_live_progress():
    """Пример live update с прогрессом задач."""
    
    from modules.tui.app import TUIApp
    
    console.print("[bold green]🚀 Пример 4: Live update с прогрессом[/bold green]\n")
    
    app = TUIApp(width=120, height=30)
    
    # Добавляем сообщения в чат
    app.add_chat_message("system", "🤖 AUTONOMOUS AI SOFTWARE ENGINEER запущен")
    app.add_chat_message("user", "Начни миграцию!")
    app.add_chat_message("ai", "ОК, начинаю анализировать проект...")
    
    # Имитация выполнения задачи с прогрессом
    task_id = "task_1"
    name = "Миграция core.py"
    
    console.print("[bold cyan]📊 Live update: выполнение задачи...[/bold cyan]")
    
    for progress in [5, 10, 25, 40, 60, 80, 95, 100]:
        app.update_task_status(task_id, "running", name=name, progress=progress)
        
        # Имитация задержки (можно заменить на реальную работу)
        import time
        time.sleep(0.2)
    
    console.print("")
    console.print("[bold green]Задача завершена![/bold green]")
    app.update_task_status(task_id, "completed", name=name, progress=100)
    
    console.print(app._build_ui())


# ─────────────────────────────────────────────
# Пример 5: Hot reload при изменении shared_context.json
# ─────────────────────────────────────────────

def example_hot_reload():
    """Пример hot reload при изменении shared_context.json."""
    
    from modules.tui.app import TUIApp
    
    console.print("[bold green]🚀 Пример 5: Hot reload[/bold green]\n")
    
    app = TUIApp(width=120, height=30)
    
    # Загружаем shared_context.json если есть
    if os.path.exists("shared_context.json"):
        with open("shared_context.json", "r") as f:
            ctx = json.load(f)
        
        console.print("[bold cyan]🔄 Hot reload: загружен shared_context.json[/bold cyan]")
        
        # Восстанавливаем задачи из shared context
        for task_id, data in ctx.get("shared_state", {}).get(
            "sdd_documents", {}
        ).items():
            app.update_task_status(
                task_id,
                "completed" if data.get("iteration", 0) > 1 else "running",
                name=f"SDD для {task_id}",
                progress=100 if data.get("iteration", 0) > 1 else 50
            )
        
        # Проверяем, был ли hot reload
        iteration_count = ctx.get("shared_state", {}).get(
            "iteration_count", 0
        )
        
        if iteration_count > 0:
            console.print(f"[yellow]🔄 Hot reload: {iteration_count} итераций[/yellow]")
    
    console.print(app._build_ui())


# ─────────────────────────────────────────────
# Пример 6: Экспорт чата в Markdown
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
    app.add_chat_message("user", "Как работает TUI?")
    app.add_chat_message("ai", "TUI использует Rich для рендеринга и Curses для input.")
    
    console.print("[bold cyan]📝 Экспорт чата в Markdown:[/bold cyan]")
    console.print(export_chat_to_markdown(app))


# ─────────────────────────────────────────────
# Пример 7: Загрузка задач из tasks.json
# ─────────────────────────────────────────────

def example_load_tasks_from_json():
    """Пример загрузки задач из tasks.json."""
    
    from modules.tui.app import TUIApp
    
    app = TUIApp(width=120, height=30)
    
    # Загружаем задачи из tasks.json если есть
    if os.path.exists("tasks.json"):
        with open("tasks.json", "r") as f:
            plan = json.load(f)
        
        console.print("[bold cyan]📋 Загрузка задач из tasks.json...[/bold cyan]")
        
        for task in plan.get("tasks", []):
            app.update_task_status(
                task["id"],
                task.get("status", "pending"),
                name=task.get("target_file", ""),
                progress=0 if task.get("status") == "pending" else 100 if task.get("status") == "completed" else None
            )
    
    console.print(app._build_ui())


# ─────────────────────────────────────────────
# Пример 8: Добавление файлов проекта
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
    app.add_file("tasks.json")
    
    console.print("[bold cyan]📁 Файлы проекта:[/bold cyan]")
    console.print(app._build_ui())


# ─────────────────────────────────────────────
# Пример 9: Мульти-задачный режим
# ─────────────────────────────────────────────

def example_multi_task():
    """Пример мульти-задачного режима."""
    
    from modules.tui.app import TUIApp
    
    app = TUIApp(width=120, height=30)
    
    # Добавляем несколько задач
    tasks = [
        ("task_1", "running", "Миграция core.py", 25),
        ("task_2", "completed", "Создание SDD", 100),
        ("task_3", "pending", "Написание тестов", 0),
        ("task_4", "failed", "Исправление ошибок", 80),
    ]
    
    for task_id, status, name, progress in tasks:
        app.update_task_status(task_id, status, name=name, progress=progress)
    
    console.print("[bold cyan]📊 Мульти-задачный режим:[/bold cyan]")
    console.print(app._build_ui())


# ─────────────────────────────────────────────
# Пример 10: Полный демо режим
# ─────────────────────────────────────────────

def example_full_demo():
    """Полный демо режим."""
    
    from modules.tui.app import TUIApp
    
    console.print("[bold green]🎬 DEMO MODE: Полный[/bold green]\n")
    
    app = TUIApp(width=120, height=30)
    
    # Добавляем сообщения
    app.add_chat_message("system", "🤖 AUTONOMOUS AI SOFTWARE ENGINEER запущен")
    app.add_chat_message("user", "Привет! Как дела?")
    app.add_chat_message("ai", "Привет! Я готов помочь с миграцией легаси-кода.")
    
    # Добавляем задачи
    app.update_task_status("task_1", "running", name="Миграция core.py", progress=25)
    app.update_task_status("task_2", "completed", name="Создание SDD")
    app.update_task_status("task_3", "pending", name="Написание тестов")
    
    # Добавляем файлы
    app.add_file("core.py")
    app.add_file("agents/migration_agent.py")
    app.add_file("modules/executor.py")
    app.add_file("shared_context.json")
    
    console.print("[bold cyan]📊 UI:[/bold cyan]")
    console.print(app._build_ui())
    console.print("")


# ─────────────────────────────────────────────
# Main CLI
# ─────────────────────────────────────────────

def main():
    """CLI интерфейс для интеграции."""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Интеграция TUI с MigrationAgent")
    parser.add_argument(
        "--example", 
        choices=[
            "simple",      # Пример 1: Простая интеграция через shared_context.json
            "events",      # Пример 2: Интеграция с event handlers (mock agent)
            "full",        # Пример 3: Интеграция с реальным MigrationAgent
            "live",        # Пример 4: Live update с прогрессом задач
            "hotreload",   # Пример 5: Hot reload при изменении shared_context.json
            "export",      # Пример 6: Экспорт чата в Markdown
            "tasksjson",   # Пример 7: Загрузка задач из tasks.json
            "files",       # Пример 8: Добавление файлов проекта
            "multitask",   # Пример 9: Мульти-задачный режим
            "full_demo",   # Пример 10: Полный демо режим
        ],
        default="full_demo",
        help="Пример интеграции"
    )
    
    args = parser.parse_args()
    
    if args.example == "simple":
        example_simple_integration()
    elif args.example == "events":
        example_event_handlers()
    elif args.example == "full":
        example_full_integration()
    elif args.example == "live":
        example_live_progress()
    elif args.example == "hotreload":
        example_hot_reload()
    elif args.example == "export":
        example_export_chat()
    elif args.example == "tasksjson":
        example_load_tasks_from_json()
    elif args.example == "files":
        example_with_file_explorer()
    elif args.example == "multitask":
        example_multi_task()
    elif args.example == "full_demo":
        example_full_demo()


if __name__ == "__main__":
    main()
