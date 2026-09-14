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

def load_prompt(role_key: str) -> str:
    """Безопасно загружает промпт из внешнего JSON-файла."""
    with open("prompts.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return data[role_key]["prompt"]

def update_prompt_file(role_key: str, new_prompt_text: str):
    """Обновляет изменяемый промпт в prompts.json."""
    with open("prompts.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    if data[role_key]["mutability"] == "immutable":
        console.print(f"[red]🚫 Попытка изменить защищенный промпт {role_key} заблокирована ядром![/red]")
        return False
        
    data[role_key]["prompt"] = new_prompt_text
    with open("prompts.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    console.print(f"[green]🧠 База знаний обновлена! Промпт [{role_key}] успешно модифицирован.[/green]")
    return True

def call_ollama(system_prompt: str, user_prompt: str) -> str:
    """Стандартизированный метод отправки запросов в Ollama."""
    payload = {
        "model": ANALYZER_MODEL,
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
