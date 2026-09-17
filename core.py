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
OLLAMA_URL = "http://192.168.5.7:11434/api/generate"
ANALYZER_MODEL = "qwen2.5-coder:14b"

# Динамически импортируем изменяемый модуль парсера
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from modules.parser import extract_code_from_markdown

# Дописать в core.py
import re
from core_tools import TOOLS_MAP

def execute_model_tools(model_response: str) -> tuple[bool, str]:
    """
    Ищет теги <call name="...">...</call> в ответе модели.
    Если находит, выполняет встроенную функцию и возвращает (True, "Результат работы инструмента").
    Если инструментов не вызвано, возвращает (False, "").
    """
    # Ищем паттерн <call name="tool_name">arguments</call>
    match = re.search(r'<call name="(\w+)">(.*?)</call>', model_response, re.DOTALL)
    
    if not match:
        return False, ""
        
    tool_name = match.group(1)
    raw_args = match.group(2).strip()
    
    if tool_name not in TOOLS_MAP:
        return True, f"Ошибка: Инструмент '{tool_name}' не зарегистрирован в ядре."
        
    console.print(f"[bold cyan]🔧 Ядро перехватило вызов инструмента: {tool_name}({raw_args})[/bold cyan]")
    
    # Парсим аргументы (если их несколько, например через запятую, или один)
    try:
        if "," in raw_args and tool_name == "read_file_chunk":
            # Специфика для чтения кусков: путь, старт, энд
            parts = [p.strip() for p in raw_args.split(",")]
            result = TOOLS_MAP[tool_name](parts[0], int(parts[1]), int(parts[2]))
        else:
            # Для простых команд типа list_dir или view_file_outline, где нужен только путь
            result = TOOLS_MAP[tool_name](raw_args)
            
        return True, f"\n<tool_result name=\"{tool_name}\">\n{result}\n</tool_result>\n"
    except Exception as e:
        return True, f"Системный сбой при выполнении инструмента: {e}"


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
    """Стандартизированный метод отправки запросов в Ollama."""
    payload = {
        "model": model_override or ANALYZER_MODEL,
        "prompt": f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{user_prompt}<|im_end|>\n<|im_start|>assistant\n",
        "stream": False,
        "options": {"temperature": 0.2}
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload)
        response.raise_for_status()
        return response.json()["response"]
    except Exception as e:
        console.print(f"[red]❌ Системный сбой при вызове Ollama: {e}[/red]")
        return ""

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
