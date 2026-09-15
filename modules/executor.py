# modules/executor.py
import os
import json
import core
from modules.parser import extract_code_from_markdown

def execute_task(task: dict, manifest: dict):
    task_id = task["id"]
    target_file = task["target_file"]
    core.console.print(f"\n[bold cyan]🎬 [Task #{task_id}] Выполнение: {target_file}[/bold cyan]")
    
    # Подготавливаем глобальные данные из манифеста
    stack_str = json.dumps(manifest["target_stack"], ensure_ascii=False, indent=2)
    constraints_str = "\n- ".join(manifest["constraints"])
    
    # ------------------------------------------------------------------
    # ЭТАП 1: SDD (Solution Design Document)
    # ------------------------------------------------------------------
    core.console.print("[yellow]📐 Чтение sdd_architect промпта...[/yellow]")
    sdd_template = core.load_prompt_from_file("sdd_architect")
    sdd_system_prompt = sdd_template.format(
        target_stack=stack_str,
        constraints=constraints_str
    )
    sdd_user_prompt = f"Задача: {task['description']}\nЦелевой файл: {target_file}"
    
    sdd_document = core.call_ollama(sdd_system_prompt, sdd_user_prompt, model_override="qwen3-coder:30b")
    core.console.print(f"[gray]📄 SDD сформирован ({len(sdd_document)} симв.)[/gray]")

    # ------------------------------------------------------------------
    # ЭТАП 2: TDD (Генерация тестов)
    # ------------------------------------------------------------------
    core.console.print("[yellow]🧪 Чтение tdd_tester промпта...[/yellow]")
    test_file_path = f"test_{os.path.basename(target_file)}"
    
    tdd_template = core.load_prompt_from_file("tdd_tester")
    test_system_prompt = tdd_template.format(sdd_document=sdd_document)
    
    raw_test_response = core.call_ollama(test_system_prompt, "Сгенерируй код тестов.")
    test_code = extract_code_from_markdown(raw_test_response)
    
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write(test_code)
    core.console.print(f"[green]💾 Тесты сохранены в: {test_file_path}[/green]")

    # ------------------------------------------------------------------
    # ЭТАП 3: Написание кода (Реализация)
    # ------------------------------------------------------------------
    core.console.print("[yellow]💻 Чтение coder_developer промпта...[/yellow]")
    coder_template = core.load_prompt_from_file("coder_developer")
    coder_system_prompt = coder_template.format(
        sdd_document=sdd_document,
        test_code=test_code,
        constraints_info=constraints_str
    )
    
    raw_code_response = core.call_ollama(coder_system_prompt, "Напиши код реализации.")
    target_code = extract_code_from_markdown(raw_code_response)
    
    os.makedirs(os.path.dirname(target_file), exist_ok=True)
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(target_code)
    core.console.print(f"[green]💾 Код сохранен в: {target_file}[/green]")

    # ------------------------------------------------------------------
    # ЭТАП 4: Валидация и Критик-Отладчик
    # ------------------------------------------------------------------
    max_fix_attempts = 3
    attempt = 0
    
    while attempt < max_fix_attempts:
        success, test_log = core.run_isolated_tests(test_file_path)
        
        if success:
            core.console.print(f"[bold green]🎉 УСПЕХ: Задача #{task_id} выполнена![/bold green]")
            update_task_status(task_id, "completed")
            return True
            
        attempt += 1
        core.console.print(f"[bold red]💥 Тесты упали. Попытка исправления {attempt}/{max_fix_attempts}[/bold red]")
        
        critic_template = core.load_prompt_from_file("critic_debugger")
        critic_system_prompt = critic_template.format(
            target_code=target_code,
            test_code=test_code,
            test_log=test_log
        )
        
        raw_fix_response = core.call_ollama(critic_system_prompt, "Исправь ошибку.")
        target_code = extract_code_from_markdown(raw_fix_response)
        
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(target_code)

    # ------------------------------------------------------------------
    # ЭТАП 5: Эволюция промптов при перманентном тупике
    # ------------------------------------------------------------------
    core.console.print(f"[red]❌ Предел попыток исправления кода исчерпан. Запускаем рефлексию над промптом...[/red]")
    
    # Вызываем мета-оптимизатор (промпт которого мы заложили в prompts.json на Шаге 1 предыдущего этапа)
    meta_optimizer_prompt = core.load_prompt("role_critic_optimizer")
    current_coder_prompt_text = core.load_prompt_from_file("coder_developer")
    
    reflector_user_prompt = (
        f"Текущий системный промпт Кодера:\n{current_coder_prompt_text}\n\n"
        f"Код, который он пишет стабильно с ошибкой:\n{target_code}\n\n"
        f"Лог ошибки тестов:\n{test_log}\n\n"
        "Какое жесткое системное правило нужно добавить в промпт Кодера, чтобы он не совершал эту ошибку? Выдай обновленный текст промпта целиком."
    )
    
    suggested_new_prompt = core.call_ollama(meta_optimizer_prompt, reflector_user_prompt, model_override="deepseek-r1:32b")
    
    # Ядро решает, записывать ли новый промпт в файл prompts/coder_developer.txt (спросит разрешения, так как там user_approved/autonomous)
    if core.update_prompt_in_file("coder_developer", suggested_new_prompt):
        core.console.print("[yellow]🔄 Промпт обновлен. Выполняем горячую перезагрузку для повторного прохождения таски с новыми знаниями...[/yellow]")
        core.hot_reload()

    update_task_status(task_id, "failed", reason=test_log)
    return False

def update_task_status(task_id: int, status: str, reason: str = ""):
    with open("tasks.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    for task in data["tasks"]:
        if task["id"] == task_id:
            task["status"] = status
            if reason: task["fail_reason"] = reason
            break
    with open("tasks.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
