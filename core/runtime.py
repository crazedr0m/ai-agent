# -*- coding: utf-8 -*-
# core/runtime.py — Функции ядра (бывший _core.py)
#
# Зона мутабельности: supervised (см. docs/adr/ADR-001-core-boundaries.md).
# Изменения требуют подтверждения человека.

import sys
import json
import subprocess
from rich.console import Console

console = Console()


def load_prompt(role_key: str) -> str:
    """Безопасно загружает промпт: из file_path или inline prompt."""
    with open("prompts.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    entry = data[role_key]
    if "file_path" in entry:
        with open(entry["file_path"], "r", encoding="utf-8") as pf:
            return pf.read()
    return entry["prompt"]


def update_prompt_file(role_key: str, new_prompt_text: str):
    """Обновляет изменяемый промпт: в файле (file_path) или inline в prompts.json."""
    with open("prompts.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    entry = data[role_key]

    if entry.get("mutability") == "immutable":
        console.print(f"[red]🚫 Попытка изменить защищенный промпт {role_key} заблокирована ядром![/red]")
        return False

    if "file_path" in entry:
        with open(entry["file_path"], "w", encoding="utf-8") as pf:
            pf.write(new_prompt_text)
        console.print(f"[green]🧠 База знаний обновлена! Файл [{entry['file_path']}] успешно модифицирован.[/green]")
    else:
        entry["prompt"] = new_prompt_text
        with open("prompts.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        console.print(f"[green]🧠 База знаний обновлена! Промпт [{role_key}] успешно модифицирован.[/green]")
    return True


def load_prompt_from_file(role_key: str) -> str:
    """Загружает промпт: из файла (file_path) или inline (prompt)."""
    with open("prompts.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    entry = data[role_key]
    if "file_path" in entry:
        with open(entry["file_path"], "r", encoding="utf-8") as pf:
            return pf.read()
    return entry["prompt"]


def update_prompt_in_file(role_key: str, new_text: str) -> bool:
    """Обновляет файл промпта с проверкой mutability (аналог update_prompt_file, но для file_path)."""
    with open("prompts.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    entry = data[role_key]
    if entry.get("mutability") == "immutable":
        console.print(f"[red]🚫 Попытка изменить защищенный промпт {role_key} заблокирована ядром![/red]")
        return False
    file_path = entry.get("file_path", f"prompts/{role_key}.txt")
    with open(file_path, "w", encoding="utf-8") as pf:
        pf.write(new_text)
    console.print(f"[green]🧠 База знаний обновлена! Файл [{file_path}] успешно модифицирован.[/green]")
    return True


def call_ollama(system_prompt: str, user_prompt: str, model_override: str = None) -> str:
    """Стандартизированный метод отправки запросов в Ollama.

    Использует OllamaAdapter из modules/llm/:
    - Основной путь: /api/chat (Ollama сам подставляет шаблон)
    - Fallback: /api/generate с ChatML для старых моделей
    - Параметры (таймаут, температура, num_ctx) — из model_profiles.json
    """
    from modules.llm import call_chat
    return call_chat(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model_override=model_override,
    )


def run_isolated_tests(test_file: str) -> tuple[bool, str]:
    """Изолированный запуск тестов с контролем returncode."""
    console.print(f"[yellow]🧪 Ядро запускает тесты {test_file}...[/yellow]")
    result = subprocess.run([sys.executable, test_file], capture_output=True, text=True)
    if result.returncode == 0:
        return True, "Успех"
    error_log = result.stderr if result.stderr else result.stdout
    return False, error_log


def hot_reload():
    """Выполняет горячую перезагрузку модулей изменяемой зоны.

    Вместо os.execv (перезапуск всего процесса) использует точечную
    перезагрузку autonomous-модулей через modules.hot_reload.
    """
    from modules.hot_reload import reload_all_autonomous, reload_all_supervised
    console.print("[bold yellow]🔄 Горячая перезагрузка autonomous-модулей...[/bold yellow]\n")
    results = reload_all_autonomous()
    success = sum(1 for v in results.values() if v)
    failed = sum(1 for v in results.values() if not v)
    console.print(f"[green]✅ Перезагружено: {success} модулей[/green]")
    if failed:
        console.print(f"[yellow]⚠️ Не удалось перезагрузить: {failed} модулей[/yellow]")
    console.print("[dim]Supervised-модули не перегружаются без подтверждения человека.[/dim]")
