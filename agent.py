import os
import sys
import re
import subprocess
import requests
from rich.console import Console
from rich.panel import Panel

console = Console()
OLLAMA_URL = "http://192.168.5.7:11434/api/generate"

ANALYZER_MODEL = "qwen2.5-coder:14b"  
CODE_FILE = "project_code.py"
TEST_FILE = "test_project.py"

def run_tests():
    """Запускает файл с тестами и возвращает результат."""
    console.print(f"[yellow]🧪 Запускаем тесты из {TEST_FILE}...[/yellow]")
    
    # Запускаем тестовый скрипт
    result = subprocess.run(
        [sys.executable, TEST_FILE],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0 and "SUCCESS" in result.stdout:
        return True, "Все тесты пройдены успешно!"
    else:
        error_log = result.stderr if result.stderr else result.stdout
        return False, error_log

def extract_code(text):
    code_blocks = re.findall(r"```(?:python)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if code_blocks:
        return code_blocks[0].strip()
    return text.strip()

def ask_ollama_to_fix_logic(error_message):
    console.print(f"[bold magenta]🤖 Вызываем {ANALYZER_MODEL} для исправления логики...[/bold magenta]")
    
    with open(CODE_FILE, "r", encoding="utf-8") as f:
        current_code = f.read()
        
    with open(TEST_FILE, "r", encoding="utf-8") as f:
        test_code = f.read()

    system_prompt = (
        "Ты — эксперт по Python. Исправь логическую ошибку в коде, чтобы тесты проходили.\n"
        "Верни ТОЛЬКО исправленный код файла `project_code.py` целиком внутри блока разметки markdown:\n"
        "```python\n"
        "код здесь\n"
        "```\n"
        "Не пиши никаких пояснений."
    )

    user_prompt = (
        f"Код тестов, который запускается:\n{test_code}\n\n"
        f"Лог падения тестов:\n{error_message}\n\n"
        f"Текущее содержимое целевого файла {CODE_FILE}:\n{current_code}\n\n"
        f"Исправь логику в {CODE_FILE}, чтобы тест прошел."
    )

    payload = {
        "model": ANALYZER_MODEL,
        "prompt": f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{user_prompt}<|im_end|>\n<|im_start|>assistant\n",
        "stream": False,
        "options": {"temperature": 0.1}
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload)
        return extract_code(response.json()["response"])
    except Exception as e:
        console.print(f"[red]❌ Ошибка: {e}[/red]")
        return None

if __name__ == "__main__":
    console.print(Panel.fit("[bold blue]Агент v0.4: Исправление логики по тестам[/bold blue]"))
    
    # 1. Запуск тестов
    success, message = run_tests()
    
    if success:
        console.print(f"[green]🎉 УСПЕХ: {message}[/green]")
        sys.exit(0)
    else:
        console.print(f"[red]💥 Тесты упали с ошибкой:\n{message}[/red]")
        
        # 2. Исправление
        fixed_code = ask_ollama_to_fix_logic(message)
        
        if fixed_code and "def add_numbers" in fixed_code:
            # 3. Применение изменений
            with open(CODE_FILE, "w", encoding="utf-8") as f:
                f.write(fixed_code)
            console.print(f"[green]💾 Файл {CODE_FILE} обновлен![/green]")
            
            # 4. Перепроверка
            success_2, message_2 = run_tests()
            if success_2:
                console.print(f"[green]🎉 Логика исправлена! Тесты прошли: {message_2}[/green]")
            else:
                console.print(f"[red]❌ Исправление не помогло: {message_2}[/red]")
