# initializer.py
import os
import sys
import json
import core
from modules.parser import extract_code_from_markdown

def scan_legacy_project(project_path: str) -> str:
    """
    Рекурсивно сканирует директорию легаси-проекта.
    Возвращает текстовую карту проекта (дерево файлов и их краткое содержимое).
    """
    if not os.path.exists(project_path):
        core.console.print(f"[red]❌ Ошибка: Папка легаси-проекта '{project_path}' не найдена![/red]")
        sys.exit(1)
        
    project_map = []
    core.console.print(f"[yellow]📂 Сканируем структуру проекта в {project_path}...[/yellow]")
    
    for root, _, files in os.walk(project_path):
        # Игнорируем виртуальные окружения и системные папки, чтобы не забивать контекст
        if any(ignored in root for ignored in ["venv", ".git", "__pycache__", ".pytest_cache"]):
            continue
            
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, project_path)
            
            # Читаем первые 50 строк каждого файла, чтобы Архитектор понял его назначение
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    head_lines = [f.readline().rstrip() for _ in range(50)]
                    content_snippet = "\n".join([line for line in head_lines if line])
            except Exception:
                content_snippet = "[Бинарный файл или ошибка чтения]"
                
            project_map.append(
                f"--- ФАЙЛ: {rel_path} ---\n"
                f"=== НАЧАЛО КОДА ===\n{content_snippet}\n=== КОНЕЦ КОДА ===\n"
            )
            
    return "\n\n".join(project_map)

def generate_migration_plan():
    core.console.print("[bold blue]🚀 Инициализация Глобального Плана с поддержкой инструментов...[/bold blue]")
    
    # 1. Читаем манифест
    with open("migration_manifest.json", "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    # 2. Получаем первичный список файлов (ls)
    import core_tools
    files_list = core_tools.list_dir(manifest["legacy_project_path"])
    
    # 3. Загружаем шаблон промпта из файла и динамически форматируем его
    core.console.print("[yellow]🧠 Загружаем динамические инструкции Глобального Архитектора...[/yellow]")
    architect_template = core.load_prompt_from_file("role_global_architect")
    
    system_instruction = architect_template.format(
        manifest_info=json.dumps(manifest, ensure_ascii=False, indent=2),
        files_structure=files_list
    )
    
    user_request = "Начни исследование проекта с помощью инструментов или выведи финальный tasks.json."
    
    # 4. Цикл интерактивного исследования ReAct (Reasoning + Acting)
    for step in range(7):
        core.console.print(f"[yellow]🤖 Шаг исследования Архитектора {step+1}/7...[/yellow]")
        raw_response = core.call_ollama(system_instruction, user_request, model_override="qwen3-coder:30b")
        
        # Проверяем, вызвала ли модель инструмент через текстовые теги
        has_tool_call, tool_result = core.execute_model_tools(raw_response)
        
        if has_tool_call:
            # Если инструмент вызван, результат передается обратно как новый запрос пользователя
            user_request = f"Результат выполнения инструмента:\n{tool_result}\n Продолжай исследование или выведи финальный план в блоке ```json."
            continue
        else:
            # Если вызовов команд больше нет — модель закончила анализ и выдала план миграции
            try:
                clean_json = extract_code_from_markdown(raw_response)
                parsed_plan = json.loads(clean_json)
                
                parsed_plan["project_name"] = manifest.get("project_name", "Универсальная миграция")
                parsed_plan["status"] = "in_progress"
                
                with open("tasks.json", "w", encoding="utf-8") as f:
                    json.dump(parsed_plan, f, indent=2, ensure_ascii=False)
                    
                core.console.print("[bold green]✨ УСПЕХ: План tasks.json построен на основе динамического анализа спагетти-кода![/bold green]")
                return True
            except Exception as e:
                core.console.print(f"[bold red]💥 Ошибка парсинга итогового плана: {e}[/bold red]")
                return False
                
    core.console.print("[red]❌ Архитектор исчерпал лимит шагов исследования и не сгенерировал план.[/red]")
    return False

if __name__ == "__main__":
    generate_migration_plan()
