# -*- coding: utf-8 -*-
"""Компоненты TUI интерфейса."""

import os
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.console import Console
from datetime import datetime


def get_file_icon(filename: str) -> str:
    """Возвращает иконку для файла в зависимости от расширения."""
    if filename.endswith(".py"):
        return "[blue]📝[/blue]"
    elif filename.endswith(".json"):
        return "[magenta]⚙️[/magenta]"
    else:
        return "[yellow]📄[/yellow]"


class ChatPanel:
    """Компонент чата с историей сообщений."""
    
    def __init__(self, history: list[tuple[str, str]], max_messages: int = 50):
        self.history = history
        self.max_messages = max_messages
        
    def render(self) -> str:
        """Рендеринг чата."""
        if not self.history:
            return "[dim]Чат пуст. Нажмите [cyan]'c'[/cyan] для отправки сообщения.[/dim]"
            
        lines = []
        for msg in reversed(self.history[-self.max_messages:]):
            role, content = msg
            prefix = "[green][bold]>[/bold][/green] Пользователь" if role == "user" else \
                     "[red][bold]<[/bold][/red] AI-Агент"
            lines.append(f"{prefix}\n{content}")
            
        return "\n\n".join(lines)


class TaskList:
    """Компонент списка задач."""
    
    def __init__(self, tasks: dict[str, dict]):
        self.tasks = tasks
        
    def render(self) -> str:
        """Рендеринг списка задач в таблице."""
        if not self.tasks:
            return "[dim]Нет активных задач.[/dim]"
            
        # Группировка по статусу
        by_status = {
            "pending": [],
            "running": [],
            "completed": [],
            "failed": [],
            "retrying": [],
        }
        
        for task_id, task in self.tasks.items():
            status = task.get("status", "pending")
            if status in by_status:
                by_status[status].append((task_id, task.get("name", "")))
            
        lines = []
        for status_icon, tasks_list in [
            ("[yellow]⏳[/yellow]", by_status["pending"]),
            ("[bold green]▶️[/bold green]", by_status["running"]),
            ("[green]✅[/green]", by_status["completed"]),
            ("[red]❌[/red]", by_status["failed"]),
            ("[orange]🔄[/orange]", by_status["retrying"]),
        ]:
            if tasks_list:
                lines.append(f"{status_icon}")
                for task_id, name in sorted(tasks_list):
                    lines.append(f"  • {task_id}: {name}")
                
        return "\n\n".join(lines)


class StatusBar:
    """Компонент статус бара."""
    
    def __init__(self, tasks: dict[str, dict], chat_history: list[tuple[str, str]], 
                 status_messages: list[tuple[str, str]]):
        self.tasks = tasks
        self.chat_history = chat_history
        self.status_messages = status_messages
        
    def render(self) -> str:
        """Рендеринг статус бара."""
        # Счётчики
        total = len([t for t in self.tasks.values() if t.get("status") != "completed"])
        completed = len([t for t in self.tasks.values() if t.get("status") == "completed"])
        
        status_lines = [
            f"[dim]Задачи: {total} в работе, {completed} завершено[/dim]",
            f"[dim]Чат: {len(self.chat_history)} сообщений[/dim]",
        ]
        
        # Последние статусы
        for timestamp, message in self.status_messages[-3:]:
            status_lines.append(f"[dim]{timestamp}: {message}[/dim]")
            
        return "\n".join(status_lines)


class FileExplorer:
    """Компонент файлового эксплорера."""
    
    def __init__(self, files: list[dict]):
        self.files = files
        
    def render(self) -> str:
        """Рендеринг файлов."""
        if not self.files:
            return "[dim]Нет файлов для отображения.[/dim]"
            
        # Группировка по папкам
        folders = {}
        for f in self.files:
            path = f.get("path", "")
            name = os.path.basename(path)
            folder = os.path.dirname(path).split(os.sep)[-1] or "root"
            if folder not in folders:
                folders[folder] = []
            folders[folder].append(name)
            
        lines = []
        for folder, files_list in sorted(folders.items()):
            lines.append(f"[bold]{folder}[/bold]:")
            
            for f_name in files_list[:10]:  # Максимум 10 файлов на папку
                icon = get_file_icon(f_name)
                lines.append(f"  {icon} {f_name}")
            if len(files_list) > 10:
                lines.append(f"  ... и ещё {len(files_list) - 10} файлов")
                
        return "\n".join(lines)
