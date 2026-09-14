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
    console.print(f"[bold magenta]🤖 Роль: Тестировщик. Генерируем тесты для {CODE_FILE}...[/bold magenta]")
    with open(CODE_FILE, "r", encoding="utf-8") as f:
        code_content = f.read()

    system_prompt = (
        "Ты — эксперт по тестированию в Python. Напиши unit-тесты для предоставленного кода.\n"
        "Тесты должны запускаться напрямую через `python test_project.py` (используй блок if __name__ == '__main__':).\n"
        "ОБЯЗАТЕЛЬНО импортируй функции из файла `project_code` (например: from project_code import ...).\n"
        "В конце успешного выполнения всех тестов скрипт ДОЛЖЕН выводить в терминал строку 'SUCCESS'.\n"
        "Верни ТОЛЬКО код файла тестов внутри блока разметки markdown:\n"
        "```python\n"
        "код тестов здесь\n"
        "```"
    )

    user_prompt = f"Напиши тесты для следующего кода:\n{code_content}"
    return call_ollama(system_prompt, user_prompt)

def ask_ollama_to_fix_tests(error_message):
    """Новая функция: Роль Критика, который чинит сломанный тест."""
    console.print(f"[bold red]🔧 Роль: Критик-Исправитель. Чиним упавшие тесты в {TEST_FILE}...[/bold red]")
    
    with open(CODE_FILE, "r", encoding="utf-8") as f:
        code_content = f.read()
    with open(TEST_FILE, "r", encoding="utf-8") as f:
        test_content = f.read()

    system_prompt = (
        "Ты — эксперт по исправлению ошибок в Python. Тесты, которые ты написал ранее, упали.\n"
        "Проанализируй лог ошибки и исправь код тестов в файле `test_project.py`.\n"
        "Убедись, что все импорты на месте (from project_code import ...).\n"
        "В конце успешного выполнения скрипт ДОЛЖЕН выводить 'SUCCESS'.\n"
        "Верни ТОЛЬКО исправленный полный код тестов в блоке markdown ```python ... ```."
    )

    user_prompt = (
        f"Целевой код проекта:\n{code_content}\n\n"
        f"Текущий сломанный код тестов:\n{test_content}\n\n"
        f"Лог ошибки из терминала:\n{error_message}"
    )
    return call_ollama(system_prompt, user_prompt)

def call_ollama(system_prompt, user_prompt):
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
        console.print(f"[red]❌ Ошибка Ollama: {e}[/red]")
        return None

def run_tests():
    console.print(f"[yellow]🧪 Запускаем тесты {TEST_FILE}...[/yellow]")
    result = subprocess.run([sys.executable, TEST_FILE], capture_output=True, text=True)
    if result.returncode == 0 and "SUCCESS" in result.stdout:
        return True, "Все тесты успешно пройдены!"
    else:
        error_log = result.stderr if result.stderr else result.stdout
        return False, error_log

if __name__ == "__main__":
    console.print(Panel.fit("[bold blue]Агент v0.6: Самокорректирующееся покрытие тестами[/bold blue]"))
    
    # 1. Если тестов нет — генерируем первую итерацию
    if not os.path.exists(TEST_FILE):
        test_code = ask_ollama_to_write_tests()
        if test_code:
            with open(TEST_FILE, "w", encoding="utf-8") as f:
                f.write(test_code)
            console.print(f"[green]💾 Создана первая версия {TEST_FILE}[/green]")

    # 2. Запускаем тесты
    success, message = run_tests()
    
    # 3. Если тесты упали — запускаем цикл самоисправления (до 3 попыток)
    attempts = 0
    while not success and attempts < 3:
        attempts += 1
        console.print(f"[yellow]⚠️ Тесты не прошли (Попытка исправления {attempts}/3). Отправляем лог на анализ...[/yellow]")
        
        fixed_test_code = ask_ollama_to_fix_tests(message)
        if fixed_test_code and "import" in fixed_test_code:
            with open(TEST_FILE, "w", encoding="utf-8") as f:
                f.write(fixed_test_code)
            console.print(f"[green]💾 Файл тестов {TEST_FILE} обновлен исправленной версией![/green]")
            
            # Проверяем снова
            success, message = run_tests()
        else:
            console.print("[red]❌ Не удалось получить адекватное исправление от ИИ.[/red]")
            break

    # 4. Финальный вердикт
    if success:
        console.print(f"[green]🎉 ПОЛНЫЙ ТРИУМФ: Робот сам написал тесты, сам нашел свою ошибку с импортом, исправил её, и тесты прошли успешно!\n{message}[/green]")
    else:
        console.print(f"[red]❌ Агенту не удалось исправить свои тесты за отведенные попытки. Лог:\n{message}[/red]")
