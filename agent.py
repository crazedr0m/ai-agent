# -*- coding: utf-8 -*-
# agent.py
import os
import sys
import json
from rich.panel import Panel

import core
import initializer
from modules.executor import execute_task

if __name__ == "__main__":
    core.console.print(Panel.fit("[bold green]🌟 AUTONOMOUS AI SOFTWARE ENGINEER v1.0 🌟[/bold green]", border_style="green"))

    # 1. Загружаем манифест миграции
    if not os.path.exists("migration_manifest.json"):
        core.console.print("[red]❌ Ошибка: Заполните migration_manifest.json перед стартом.[/red]")
        sys.exit(1)
        
    with open("migration_manifest.json", "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # 2. Если файла задач tasks.json нет — запускаем инициализатор для его генерации
    if not os.path.exists("tasks.json"):
        core.console.print("[yellow]📋 Реестр задач не найден. Запускаем фазу стратегического планирования...[/yellow]")
        success = initializer.generate_migration_plan()
        if not success:
            core.console.print("[red]❌ Не удалось инициализировать проект. Конвейер остановлен.[/red]")
            sys.exit(1)

    # 3. ГЛАВНЫЙ ИТЕРАЦИОННЫЙ КОНВЕЙЕР (Работа в режиме 24/7)
    core.console.print("[bold green]🚀 Конвейер запущен! Начинаем обработку реестра задач...[/bold green]")
    
    while True:
        with open("tasks.json", "r", encoding="utf-8") as f:
            plan = json.load(f)
            
        # Ищем первую задачу, которая ожидает выполнения (pending)
        current_task = next((t for t in plan["tasks"] if t["status"] == "pending"), None)
        
        if not current_task:
            core.console.print(Panel.fit("[bold green]🎉🎉🎉 ТРИУМФ! Все задачи из реестра tasks.json успешно выполнены!\nПроект полностью мигрирован согласно манифесту.[/bold green]", border_style="green"))
            sys.exit(0)
            
        # Меняем статус задачи на "in_progress", чтобы зафиксировать выполнение
        current_task["status"] = "in_progress"
        with open("tasks.json", "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2, ensure_ascii=False)
            
        # Отдаем задачу универсальному модулю исполнения (Исполнитель -> Тестер -> Критик)
        task_success = execute_task(current_task, manifest)
        
        if not task_success:
            core.console.print(f"[yellow]⚠️ Задача #{current_task['id']} завершилась неудачей или пропущена. Конвейер переходит к следующей таске.[/yellow]")
            # Если задача упала, обновляем её статус в tasks.json на failed, чтобы цикл не застрял на ней
            current_task["status"] = "failed"
            with open("tasks.json", "w", encoding="utf-8") as f:
                json.dump(plan, f, indent=2, ensure_ascii=False)
