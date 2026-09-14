import os
import sys
import subprocess
import requests
from rich.panel import Panel

import core
# Динамически импортируем наш парсер
import modules.parser

CODE_FILE = "project_code.py"
TEST_FILE = "test_project.py"

def extract_clean_code_built_in(raw_text: str) -> str:
    """
    Бронебойный построчный парсер. 
    Игнорирует мусорные пробелы справа и собирает код строго между бэктиками.
    """
    lines = raw_text.splitlines()
    code_lines = []
    inside_block = False
    
    for line in lines:
        cleaned_line = line.rstrip() # Удаляем мусорные пробелы справа, из-за которых рвутся строки
        
        if cleaned_line.startswith("```"):
            if not inside_block:
                inside_block = True
                continue
            else:
                inside_block = False
                continue
                
        if inside_block:
            code_lines.append(cleaned_line)
            
    return "\n".join(code_lines).strip()

def ask_ai_to_fix_parser_module(bad_response: str) -> str:
    """Роль Мета-Программиста с полной очисткой строк."""
    core.console.print("[bold magenta]🤖 Роль: Мета-Программист. Исправляем код модуля modules/parser.py...[/bold magenta]")
    
    with open("modules/parser.py", "r", encoding="utf-8") as f:
        current_parser_code = f.read()

    system_prompt = (
        "Ты — компилятор кода. Твоя единственная задача — выдать валидный код для файла `modules/parser.py`.\n"
        "Ты должен начать свой ответ СРАЗУ с открывающего тега ```python и закончить тегом ```.\n"
        "Запрещено писать любые приветствия, комментарии или пояснения вне блока кода. "
        "Перепиши функцию `extract_code_from_markdown`, чтобы она использовала флаг re.IGNORECASE "
        "и была устойчива к любому регистру символов в тегах."
    )

    user_prompt = f"Текущий код:\n{current_parser_code}"
    
    payload = {
        "model": core.ANALYZER_MODEL,
        "prompt": f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{user_prompt}<|im_end|>\n<|im_start|>assistant\n",
        "stream": False,
        "options": {
            "temperature": 0.0,
            "stop": ["<|im_end|>", "User:", "\n\n# Объяснение"]
        }
    }

    try:
        response = requests.post(core.OLLAMA_URL, json=payload)
        response.raise_for_status()
        raw_fix = response.json()["response"]
        
        # ВЫВОДИМ ТОЧНЫЙ ОТВЕТ МОДЕЛИ ДЛЯ ОТЛАДКИ
        core.console.print(Panel(raw_fix, title="[cyan]Сырой ответ модели (Raw Output)[/cyan]", border_style="cyan"))
        
        # Используем наш новый построчный очиститель
        return extract_clean_code_built_in(raw_fix)
    except Exception as e:
        core.console.print(f"[red]❌ Ошибка вызова ИИ: {e}[/red]")
        return ""

if __name__ == "__main__":
    core.console.print(Panel.fit("[bold blue]Архитектурный Агент v0.8: Самомодификация кода[/bold blue]"))

    system_instruction = "Напиши код unit-теста для Python."
    user_request = "Выдай пример простого pass теста."
    
    core.console.print("[yellow]⏳ Запрашиваем у Ollama ответ...[/yellow]")
    raw_response = core.call_ollama(system_instruction, user_request)

    extracted_code = modules.parser.extract_code_from_markdown(raw_response)
        
    if not extracted_code:
        core.console.print("[bold red]💥 СБОЙ: Модуль modules/parser.py вернул пустую строку! Начинаем саморемонт...[/bold red]")
        
        new_parser_code = ask_ai_to_fix_parser_module(raw_response)
        
        if new_parser_code and "def extract_code_from_markdown" in new_parser_code:
            temp_file = "modules/parser_temp.py"
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(new_parser_code)
                
            # Проверяем компиляцию нового кода
            check_syntax = subprocess.run([sys.executable, "-m", "py_compile", temp_file], capture_output=True, text=True)
            
            if check_syntax.returncode == 0:
                core.console.print("[green]✅ Проверка синтаксиса нового модуля прошла успешно![/green]")
                os.replace(temp_file, "modules/parser.py")
                core.console.print("[bold green]💾 Модуль modules/parser.py успешно обновлен собственным кодом агента![/bold green]")
                core.hot_reload()
            else:
                core.console.print(Panel(check_syntax.stderr, title="[bold red]❌ Ошибка синтаксиса в сгенерированном коде[/bold red]", border_style="red"))
                if os.path.exists(temp_file): os.remove(temp_file)
        else:
            core.console.print("[red]❌ Не удалось получить исправленный код модуля от ИИ.[/red]")
