# -*- coding: utf-8 -*-
# core.py
# НЕИЗМЕНЯЕМОЕ ЯДРО СИСТЕМЫ. ИИ не имеет права менять этот файл.

import os
import sys
import json
import subprocess
import requests
from rich.console import Console
from rich.panel import Panel

# Инициализируем компоненты
console = Console()
OLLAMA_URL = "http://192.168.5.7:11434/api/chat"
ANALYZER_MODEL = "qwen2.5-coder:14b"

# Динамически импортируем изменяемый модуль парсера
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from modules.parser import extract_code_from_markdown

# execute_model_tools удалён (дубль ReActEngine.execute_tool_call в core/core.py)


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
        # Запись через file_path — пишем в файл на диске
        with open(entry["file_path"], "w", encoding="utf-8") as pf:
            pf.write(new_prompt_text)
        console.print(f"[green]🧠 База знаний обновлена! Файл [{entry['file_path']}] успешно модифицирован.[/green]")
    else:
        # Запись через inline prompt — пишем в JSON
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
    """Выполняет горячую перезагрузку процесса в памяти."""
    console.print("[bold yellow]🔄 Выполняется горячая перезагрузка архитектуры ядра...[/bold yellow]\n")
    os.execv(sys.executable, [sys.executable] + sys.argv)
