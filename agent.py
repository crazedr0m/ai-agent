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

def extract_code(text):
    code_blocks = re.findall(r"```(?:python)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if code_blocks:
        return code_blocks[0].strip()
    return text.strip()

def ask_ollama_to_write_tests():
    """Агент анализирует код и пишет под него unit-тесты."""
    console.print(f"[bold magenta]🤖 Роль: Тестировщик. Генерируем тесты для {CODE_FILE}...[/bold magenta]")
    
    with open(CODE_FILE, "r", encoding="utf-8") as f:
        code_content = f.read()

    system_prompt = (
        "Ты — эксперт по тестированию в Python. Напиши unit-тесты для предоставленного кода.\n"
        "Тесты должны запускаться напрямую через `python test_project.py` (используй блок if __name__ == '__main__':).\n"
        "В конце успешного выполнения всех тестов скрипт ДОЛЖЕН выводить в терминал строку 'SUCCESS'.\n"
        "Верни ТОЛЬКО код файла тестов внутри блока разметки markdown:\n"
        "```python\n"
        "код тестов здесь\n"
        "```\n"
        "Не пиши никаких приветствий или пояснений."
    )

    user_prompt = f"Напиши тесты для следующего кода:\n{code_content}"

    payload = {
        "model": ANALYZER_MODEL,
        "prompt": f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{user_prompt}<|im_end|>\n<|im_start|>assistant\n",
        "stream": False,
        "options": {"temperature": 0.2}
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload)
        return extract_code(response.json()["response"])
    except Exception as e:
        console.print(f"[red]❌ Ошибка генерации тестов: {e}[/red]")
        return None

def run_tests():
    """Запускает созданный файл с тестами."""
    console.print(f"[yellow]🧪 Запускаем созданные тесты {TEST_FILE}...[/yellow]")
    
    result = subprocess.run(
        [sys.executable, TEST_FILE],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0 and "SUCCESS" in result.stdout:
        return True, "Все сгенерированные тесты успешно пройдены!"
    else:
        error_log = result.stderr if result.stderr else result.stdout
        return False, error_log

if __name__ == "__main__":
    console.print(Panel.fit("[bold blue]Агент v0.5: Автономное покрытие кодом тестов[/bold blue]"))
    
    # 1. Проверяем, есть ли тесты. Если нет — создаем.
    if not os.path.exists(TEST_FILE):
        console.print(f"[yellow]📂 Файл тестов {TEST_FILE} не найден. Начинаем генерацию...[/yellow]")
        test_code = ask_ollama_to_write_tests()
        
        if test_code and "import" in test_code:
            with open(TEST_FILE, "w", encoding="utf-8") as f:
                f.write(test_code)
            console.print(f"[green]💾 Робот успешно создал файл тестов: {TEST_FILE}[/green]")
        else:
            console.print("[red]❌ Не удалось сгенерировать валидный код тестов.[/red]")
            sys.exit(1)
            
    # 2. Запускаем получившиеся тесты
    success, message = run_tests()
    
    if success:
        console.print(f"[green]🎉 ТРИУМФ: Робот сам написал тесты, и они успешно выполнились!\n{message}[/green]")
    else:
        console.print(f"[red]💥 Ошибка при запуске созданных роботом тестов:\n{message}[/red]")
