# agent.py
import os
import sys
from rich.panel import Panel

# Импортируем неизменяемые системные функции ядра
import core
from modules.parser import extract_code_from_markdown

CODE_FILE = "project_code.py"
TEST_FILE = "test_project.py"

if __name__ == "__main__":
    core.console.print(Panel.fit("[bold blue]Архитектурный Агент v0.7: Модульная структура[/bold blue]"))

    # 1. Если файла тестов нет, запускаем роль Тестировщика
    if not os.path.exists(TEST_FILE):
        # Загружаем инструкцию из внешней конфигурации prompts.json
        system_instruction = core.load_prompt("role_tester")
        
        with open(CODE_FILE, "r", encoding="utf-8") as f:
            code_content = f.read()
            
        user_request = f"Напиши тесты для следующего кода:\n{code_content}"
        
        # Запрос к локальной модели через ядро
        raw_response = core.call_ollama(system_instruction, user_request)
        test_code = extract_code_from_markdown(raw_response)
        
        if test_code and "import" in test_code:
            with open(TEST_FILE, "w", encoding="utf-8") as f:
                f.write(test_code)
            core.console.print(f"[green]💾 Модуль тестирования создал файл: {TEST_FILE}[/green]")
        else:
            core.console.print("[red]❌ Ошибка: модель выдала невалидный код тестов.[/red]")
            sys.exit(1)

    # 2. Выполняем изолированную проверку силами ядра
    success, log_message = core.run_isolated_tests(TEST_FILE)
    
    if success:
        core.console.print("[bold green]🎉 ТРИУМФ: Архитектура v0.7 работает идеально! Тесты пройдены.[/bold green]")
        sys.exit(0)
    else:
        core.console.print(f"[red]💥 Ошибка при прохождении тестов:\n{log_message}[/red]")
        core.console.print("[yellow]💡 Система готова к запуску эволюционного цикла исправлений...[/yellow]")
        # Здесь в следующем шаге мы подключим автоматическую модификацию модулей и промптов
