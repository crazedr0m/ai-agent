# -*- coding: utf-8 -*-
# initializer.py
import os
import sys
import json
import core
from modules.parser import extract_code_from_markdown, has_json_block

MAX_REACT_STEPS = 7
MAX_RETRIES = 3


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
        if any(ignored in root for ignored in ["venv", ".git", "__pycache__", ".pytest_cache"]):
            continue

        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, project_path)

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


def attempt_meta_recovery(raw_response: str, error: Exception, step: int) -> bool:
    """
    Meta-Optimizer: анализирует системную ошибку, чинит код или промпт,
    затем выполняет hot reload для повторной попытки.
    """
    core.console.print("[bold yellow]🧠 Meta-Optimizer: диагностика системной ошибки...[/bold yellow]")

    # Загружаем контекст для анализа
    try:
        parser_code = open("modules/parser.py", "r", encoding="utf-8").read()
    except Exception:
        parser_code = "[не удалось прочитать]"

    try:
        architect_prompt = core.load_prompt_from_file("role_global_architect1")
    except Exception:
        architect_prompt = "[не удалось загрузить]"

    meta_system = core.load_prompt_from_file("meta_recovery_system")
    meta_user_template = core.load_prompt_from_file("meta_recovery_user")
    meta_user_prompt = meta_user_template.format(
        step=step + 1,
        error=error,
        raw_response=raw_response[:2000],
        parser_code=parser_code,
        architect_prompt=architect_prompt
    )

    diagnosis_raw = core.call_ollama(
        meta_system,
        meta_user_prompt,
        model_override="deepseek-r1:32b"
    )

    # Парсим диагноз
    try:
        clean = extract_code_from_markdown(diagnosis_raw)
        if not clean:
            # Возможно deepseek вернул просто JSON без ```json
            clean = diagnosis_raw.strip()
        diag = json.loads(clean)
    except Exception as e:
        core.console.print(f"[red]❌ Meta-Optimizer не смог диагностировать: {e}[/red]")
        core.console.print(f"[dim]Сырой ответ: {diagnosis_raw[:500]}[/dim]")
        return False

    fix_type = diag.get("fix_type", "none")
    target_file = diag.get("target_file", "")
    new_content = diag.get("new_content", "")

    if fix_type == "none" or not new_content:
        core.console.print("[yellow]⚠️ Meta-Optimizer не предложил фикс. Ручное вмешательство.[/yellow]")
        return False

    if fix_type == "code" and target_file:
        # Проверка: не пишем в immutable-файлы (core.py, core_tools.py)
        if target_file in ("core.py", "core_tools.py"):
            core.console.print(f"[red]🚫 Meta-Optimizer пытался изменить {target_file} — заблокировано![/red]")
            return False

        with open(target_file, "w", encoding="utf-8") as f:
            f.write(new_content)
        core.console.print(f"[bold green]✅ {target_file} исправлен Meta-Optimizer![/bold green]")
        core.console.print("[bold yellow]🔄 Hot reload...[/bold yellow]")
        core.hot_reload()
        return True

    if fix_type == "prompt" and target_file:
        # Проверка через prompts.json mutability
        try:
            success = core.update_prompt_in_file(
                target_file.replace("prompts/", "").replace(".txt", ""),
                new_content
            )
            if success:
                core.console.print("[bold yellow]🔄 Промпт обновлён. Hot reload...[/bold yellow]")
                core.hot_reload()
                return True
            else:
                core.console.print("[yellow]⚠️ Промпт immutable — фикс отклонён ядром.[/yellow]")
                return False
        except Exception as e:
            core.console.print(f"[red]❌ Ошибка при обновлении промпта: {e}[/red]")
            return False

    core.console.print(f"[red]❌ Неизвестный fix_type={fix_type} или пустой target_file.[/red]")
    return False


def generate_migration_plan():
    core.console.print("[bold blue]🚀 Инициализация Глобального Плана с поддержкой инструментов...[/bold blue]")

    # 1. Читаем манифест
    with open("migration_manifest.json", "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # 2. Получаем первичный список файлов (ls)
    import core_tools
    files_list = core_tools.list_dir(manifest["legacy_project_path"])

    # 3. Загружаем шаблон промпта
    core.console.print("[yellow]🧠 Загружаем динамические инструкции Глобального Архитектора (с поддержкой инструментов)...[/yellow]")
    architect_template = core.load_prompt_from_file("role_global_architect1")

    system_instruction = architect_template.format(
        manifest_info=json.dumps(manifest, ensure_ascii=False, indent=2),
        files_structure=files_list
    )

    user_request = "Начни исследование проекта с помощью инструментов или выведи финальный tasks.json."

    # ---- Внешний цикл retries ----
    for attempt in range(MAX_RETRIES):
        if attempt > 0:
            core.console.print(f"[yellow]🔄 Retry #{attempt + 1}/{MAX_RETRIES}...[/yellow]")

        # ---- ReAct-цикл ----
        for step in range(MAX_REACT_STEPS):
            core.console.print(f"[yellow]🤖 Шаг исследования Архитектора {step + 1}/{MAX_REACT_STEPS}...[/yellow]")
            raw_response = core.call_ollama(system_instruction, user_request, model_override="qwen3-coder:30b")

            if not raw_response:
                core.console.print("[red]❌ Пустой ответ от модели. Retry...[/red]")
                break

            # Проверяем вызов инструментов
            has_tool_call, tool_result = core.execute_model_tools(raw_response)

            if has_tool_call:
                user_request = (
                    f"Результат выполнения инструмента:\n{tool_result}\n"
                    "Продолжай исследование или выведи финальный план в блоке ```json."
                )
                continue

            # --- Умный парсинг: парсим JSON только если есть ```json блок ---
            clean_json = extract_code_from_markdown(raw_response)

            if not clean_json:
                # Модель не вызвала инструмент и не вывела JSON — она ещё думает
                core.console.print("[dim]💭 Модель ещё исследует проект...[/dim]")
                user_request = (
                    "Продолжай исследование или выведи финальный план в блоке ```json. "
                    "Не выводи ```json, пока не готов."
                )
                continue

            # Есть JSON-блок — пробуем распарсить
            try:
                parsed_plan = json.loads(clean_json)

                # Валидация: проверяем, что это tasks.json
                if "tasks" not in parsed_plan or not isinstance(parsed_plan["tasks"], list):
                    raise ValueError("Нет поля 'tasks' или это не список")

                parsed_plan["project_name"] = manifest.get("project_name", "Универсальная миграция")
                parsed_plan["status"] = "in_progress"

                with open("tasks.json", "w", encoding="utf-8") as f:
                    json.dump(parsed_plan, f, indent=2, ensure_ascii=False)

                core.console.print("[bold green]✨ УСПЕХ: План tasks.json построен на основе динамического анализа спагетти-кода![/bold green]")
                return True

            except (json.JSONDecodeError, ValueError) as e:
                core.console.print(f"[bold red]💥 Ошибка парсинга JSON (попытка {attempt + 1}/{MAX_RETRIES}, шаг {step + 1}): {e}[/bold red]")

                # Если ещё есть retry-попытки — передаём ошибку модели как новый user_request
                if attempt < MAX_RETRIES - 1 or step < MAX_REACT_STEPS - 1:
                    user_request = (
                        f"Твой JSON не прошел валидацию: {e}\n"
                        f"Твой ответ: {raw_response[:1000]}\n"
                        "Исправь JSON и выведи снова в ```json. "
                        "Убедись, что есть поле 'tasks' с массивом задач."
                    )
                    continue

                # Исчерпали все retry + шаги — запускаем Meta-Optimizer
                core.console.print("[bold yellow]🔥 Все попытки исчерпаны. Запуск Meta-Optimizer...[/bold yellow]")
                if attempt_meta_recovery(raw_response, e, step):
                    # Meta-Optimizer сделал hot reload — процесс перезапущен
                    return True

                core.console.print("[red]❌ Meta-Optimizer не смог исправить. Конвейер остановлен.[/red]")
                return False

        # Если внутренний цикл закончился без return — продолжаем внешний retry
        # Сбрасываем user_request для новой попытки
        user_request = "Начни исследование проекта с помощью инструментов или выведи финальный tasks.json."

    core.console.print("[red]❌ Архитектор исчерпал лимит попыток и не сгенерировал план.[/red]")
    return False


if __name__ == "__main__":
    generate_migration_plan()
