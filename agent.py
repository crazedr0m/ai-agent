# Псевдокод универсального главного цикла agent.py

import json
import os
import core

def bootstrap_migration():
    # 1. Читаем манифест
    with open("migration_manifest.json", "r") as f:
        manifest = json.load(f)
        
    # 2. Если плана tasks.json еще нет — вызываем Архитектора
    if not os.path.exists("tasks.json"):
        core.console.print("[blue]🔍 Сканируем легаси каталог и составляем план...[/blue]")
        
        # Получаем структуру файлов легаси-проекта
        legacy_files = str(os.listdir(manifest["legacy_project_path"]))
        
        # Форматируем промпт Архитектора данными из манифеста
        arch_prompt = core.load_prompt("role_global_architect").format(
            target_stack=json.dumps(manifest["target_stack"], ensure_ascii=False),
            constraints="\n- ".join(manifest["constraints"]),
            strategy=manifest["strategy"],
            files_structure=legacy_files
        )
        
        # Вызываем тяжелую модель (30B+) для планирования
        raw_plan = core.call_ollama_heavy(arch_prompt, "Создай план миграции.")
        tasks_json = core.modules.parser.extract_code_from_markdown(raw_plan)
        
        with open("tasks.json", "w") as f:
            f.write(tasks_json)
            
    # 3. ГЛАВНЫЙ ЦИКЛ ВЫПОЛНЕНИЯ (24/7)
    while True:
        with open("tasks.json", "r") as f:
            plan = json.load(f)
            
        # Ищем первую задачу в статусе pending
        current_task = next((t for t in plan["tasks"] if t["status"] == "pending"), None)
        
        if not current_task:
            core.console.print("[green]🎉 Миграция проекта успешно завершена![/green]")
            break
            
        # Запускаем SDD -> TDD цикл для этой конкретной задачи
        execute_task(current_task, manifest)
