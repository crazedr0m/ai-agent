# -*- coding: utf-8 -*-
"""Пример запуска TUI приложения."""

import os
import json
from datetime import datetime

from modules.tui.app import TUIApp


def create_sample_tasks():
    """Создание тестовых задач для демонстрации."""
    
    tasks = {
        "task_1": {
            "id": "task_1",
            "name": "Миграция legacy_src/app.py → modern_src/",
            "status": "running",
            "progress": 45,
            "attempts": 1,
        },
        "task_2": {
            "id": "task_2", 
            "name": "Сканирование legacy_src/models.py",
            "status": "completed",
            "progress": 100,
            "attempts": 1,
        },
        "task_3": {
            "id": "task_3",
            "name": "Генерация тестов для legacy_src/utils.py",
            "status": "pending",
            "progress": 0,
            "attempts": 1,
        },
    }
    
    return tasks


def create_sample_chat():
    """Создание истории чата."""
    
    chat = [
        ("user", "Привет! Начни миграцию проекта."),
        ("AI-Агент", "👋 Привет! Я готов к работе. Загружаю манифест..."),
        ("AI-Агент", "✅ Манифест загружен. Стартую сканирование legacy_src/"),
        ("user", "Отлично, жду прогресс."),
    ]
    
    return chat


def create_sample_files():
    """Создание списка файлов проекта."""
    
    files = [
        {"path": "./legacy_src/app.py"},
        {"path": "./legacy_src/models.py"},
        {"path": "./legacy_src/utils.py"},
        {"path": "./modern_src/app.py"},
        {"path": "./modern_src/models.py"},
        {"path": "./migration_manifest.json"},
        {"path": "./tasks.json"},
    ]
    
    return files


def main():
    """Главная функция."""
    
    print("\n" + "="*60)
    print("🤖 AUTONOMOUS AI SOFTWARE ENGINEER v1.0")
    print("="*60 + "\n")
    
    # Создаём TUI приложение
    app = TUIApp(width=80, height=24)
    
    # Загружаем sample данные (в реальной версии — из файлов/агента)
    tasks = create_sample_tasks()
    chat_history = create_sample_chat()
    project_files = create_sample_files()
    
    # Устанавливаем state
    app.tasks = tasks
    app.chat_history = chat_history
    app.project_files = project_files
    
    print("[green]🚀 TUI интерфейс запущен![/green]")
    print(f"[dim]Ширина: {app.width}, Высота: {app.height}[/dim]\n")
    
    # В реальной версии здесь запускается event loop
    # app.run()
    
    print("\n[bold yellow]⚠️ Это демо-режим.[/bold yellow]")
    print("[dim]Для запуска полной версии используйте:[/dim]")
    print("[cyan]python -m modules.tui[/cyan]\n")


if __name__ == "__main__":
    main()
