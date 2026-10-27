# -*- coding: utf-8 -*-
# modules/dev_tools.py — Инструменты разработчика (Фаза 2)
#
# Минимальный набор:
# - read_file       — чтение файла (свободно)
# - write_file      — запись файла (с подтверждением)
# - apply_diff      — точечное изменение (с подтверждением)
# - search_code     — grep по проекту (свободно)
# - run_command     — запуск команды (с подтверждением)
# - git_status      — git status (свободно)
# - git_diff        — git diff (свободно)
# - git_commit      — git commit (с подтверждением)
#
# Система разрешений (2.3):
# - read: свободно
# - write: подтверждение (permit/deny)
# - dangerous: подтверждение + лог

import os
import re
import subprocess
import sys
from typing import Optional

from core.core_tools import register_tool

# ──────────────────────────────────────────────
# Система разрешений (2.3)
# ──────────────────────────────────────────────

_PERMISSION_LEVELS = {
    "read": "free",       # чтение — свободно
    "write": "confirm",   # запись — с подтверждением
    "dangerous": "confirm",  # опасные операции — с подтверждением
}


def set_permission_level(category: str, level: str):
    """Изменить уровень разрешения для категории."""
    if category in _PERMISSION_LEVELS:
        _PERMISSION_LEVELS[category] = level


def get_permission_level(category: str) -> str:
    """Получить уровень разрешения для категории."""
    return _PERMISSION_LEVELS.get(category, "confirm")


def _confirm_action(description: str, category: str = "write") -> bool:
    """Запросить подтверждение у пользователя.

    Возвращает True если разрешено, False если запрещено.
    """
    level = get_permission_level(category)

    if level == "free":
        return True

    if level == "deny":
        from rich.console import Console
        Console().print(f"[red]🚫 Заблокировано: {description}[/red]")
        return False

    # confirm — спрашиваем пользователя
    from rich.console import Console
    console = Console()

    console.print(f"\n[yellow]🔐 Разрешение: {description}[/yellow]")
    console.print("[dim]Разрешить? (y/n, всегда для сессии — Y/N)[/dim]")

    try:
        import curses
        stdscr = curses.initscr()
        curses.curs_set(1)
        stdscr.addstr(0, 0, f"Разрешить? (y/n, Y/N): ".ljust(80))
        stdscr.refresh()

        response = ""
        while True:
            key = stdscr.getch()
            if key in [ord('y'), ord('Y'), ord('n'), ord('N'), 10, 13, 27]:
                if key == 27:  # ESC
                    response = "n"
                    break
                elif key in [10, 13]:  # Enter
                    if response:
                        break
                else:
                    response = chr(key)
                    break
            elif key == curses.KEY_BACKSPACE or key == 127:
                response = ""
                stdscr.move(0, 0)
                stdscr.clrtoe()
                stdscr.addstr(0, 0, f"Разрешить? (y/n, Y/N): ".ljust(80))
                stdscr.refresh()

        curses.endwin()
    except Exception:
        # fallback на консольный ввод
        response = input("Разрешить? (y/n, Y/N): ").strip().lower()

    if response == 'Y':
        # Всегда для сессии
        set_permission_level(category, "free")
        console.print(f"[green]✅ {category}: разрешено на сессию[/green]")
        return True
    elif response == 'y':
        return True
    elif response == 'N':
        set_permission_level(category, "deny")
        console.print(f"[red]🚫 {category}: заблокировано на сессию[/red]")
        return False
    else:
        return False


# ──────────────────────────────────────────────
# Инструменты
# ──────────────────────────────────────────────


@register_tool("read_file", "Прочитать содержимое файла (свободно)")
def read_file(file_path: str, start_line: int = 1, end_line: int = 0) -> str:
    """Прочитать диапазон строк из файла.

    Args:
        file_path: путь к файлу
        start_line: начальная строка (1-based)
        end_line: конечная строка (0 = до конца файла)
    """
    try:
        lines = []
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f, 1):
                if i < start_line:
                    continue
                if end_line > 0 and i > end_line:
                    break
                lines.append(f"{i}: {line.rstrip()}")
        if not lines:
            return f"[пусто] Файл {file_path} не содержит строк в диапазоне {start_line}-{end_line}"
        return "\n".join(lines)
    except FileNotFoundError:
        return f"Ошибка: файл '{file_path}' не найден"
    except Exception as e:
        return f"Ошибка чтения файла: {e}"


@register_tool("write_file", "Записать содержимое в файл (с подтверждением)")
def write_file(file_path: str, content: str) -> str:
    """Записать содержимое в файл (полная перезапись).

    Args:
        file_path: путь к файлу
        content: новое содержимое файла
    """
    if not _confirm_action(f"Запись файла: {file_path} ({len(content)} символов)"):
        return "❌ Операция отклонена пользователем"

    try:
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"✅ Файл {file_path} записан ({len(content)} символов)"
    except Exception as e:
        return f"Ошибка записи файла: {e}"


@register_tool("apply_diff", "Применить точечные изменения к файлу (с подтверждением)")
def apply_diff(file_path: str, old_string: str, new_string: str) -> str:
    """Заменить old_string на new_string в файле.

    Args:
        file_path: путь к файлу
        old_string: строка для замены (должна точно совпадать)
        new_string: новая строка
    """
    if not _confirm_action(f"Изменение файла: {file_path}"):
        return "❌ Операция отклонена пользователем"

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if old_string not in content:
            return f"Ошибка: строка для замены не найдена в {file_path}"

        new_content = content.replace(old_string, new_string, 1)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        return f"✅ Изменение применено к {file_path}"
    except Exception as e:
        return f"Ошибка применения diff: {e}"


@register_tool("search_code", "Поиск по коду проекта (grep, свободно)")
def search_code(pattern: str, path: str = ".", file_pattern: str = "*.py") -> str:
    """Поиск по коду с помощью grep.

    Args:
        pattern: регулярное выражение для поиска
        path: директория для поиска
        file_pattern: glob-паттерн для файлов (по умолчанию *.py)
    """
    try:
        # Используем grep если доступен
        grep_cmd = ["grep", "-rn", "--include", file_pattern, pattern, path]
        result = subprocess.run(
            grep_cmd, capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            output = result.stdout.strip()
            lines = output.split("\n")
            if len(lines) > 100:
                output = "\n".join(lines[:100]) + f"\n... и ещё {len(lines) - 100} совпадений"
            return output or "Совпадений не найдено"
        else:
            return "Совпадений не найдено"
    except FileNotFoundError:
        # fallback на Python-реализацию
        return _search_python(pattern, path, file_pattern)
    except subprocess.TimeoutExpired:
        return "Ошибка: поиск превысил таймаут (30с)"
    except Exception as e:
        return f"Ошибка поиска: {e}"


def _search_python(pattern: str, path: str, file_pattern: str) -> str:
    """Python-fallback для grep."""
    import fnmatch
    results = []
    pattern_re = re.compile(pattern)

    for root, dirs, files in os.walk(path):
        # Пропускаем venv, .git, __pycache__
        dirs[:] = [d for d in dirs if d not in ("venv", ".git", "__pycache__", ".pytest_cache")]

        for f in files:
            if not fnmatch.fnmatch(f, file_pattern):
                continue
            filepath = os.path.join(root, f)
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as fh:
                    for i, line in enumerate(fh, 1):
                        if pattern_re.search(line):
                            rel = os.path.relpath(filepath, path)
                            results.append(f"{rel}:{i}:{line.rstrip()}")
            except Exception:
                pass

    if not results:
        return "Совпадений не найдено"

    output = "\n".join(results[:100])
    if len(results) > 100:
        output += f"\n... и ещё {len(results) - 100} совпадений"
    return output


@register_tool("run_command", "Запустить команду в shell (с подтверждением)")
def run_command(command: str, timeout: int = 60) -> str:
    """Запустить shell-команду и вернуть результат.

    Args:
        command: команда для выполнения
        timeout: таймаут в секундах (по умолчанию 60)
    """
    if not _confirm_action(f"Запуск команды: {command}", category="dangerous"):
        return "❌ Операция отклонена пользователем"

    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=timeout
        )
        output_parts = []
        if result.stdout:
            output_parts.append(f"[stdout]\n{result.stdout[:2000]}")
        if result.stderr:
            output_parts.append(f"[stderr]\n{result.stderr[:2000]}")
        if not output_parts:
            output_parts.append("[пустой вывод]")

        output = "\n".join(output_parts)
        status = f"✅ Команда выполнена (exit code: {result.returncode})"
        return f"{status}\n{output}"
    except subprocess.TimeoutExpired:
        return f"❌ Команда превысила таймаут ({timeout}с)"
    except Exception as e:
        return f"Ошибка выполнения команды: {e}"


@register_tool("git_status", "Показать git status (свободно)")
def git_status() -> str:
    """Показать текущее состояние git-репозитория."""
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return "Не git-репозиторий или git недоступен"

        branch_result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, timeout=5
        )
        branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "?"

        output = f"🌿 Ветка: {branch}\n"
        if result.stdout.strip():
            output += f"Изменения:\n{result.stdout}"
        else:
            output += "Чистое рабочее дерево"
        return output
    except Exception as e:
        return f"Ошибка git status: {e}"


@register_tool("git_diff", "Показать git diff (свободно)")
def git_diff(staged: bool = False) -> str:
    """Показать незакоммиченные изменения.

    Args:
        staged: показать только staged изменения
    """
    try:
        cmd = ["git", "diff"]
        if staged:
            cmd.append("--staged")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            output = result.stdout.strip()
            if not output:
                return "Нет изменений"
            if len(output) > 3000:
                output = output[:3000] + "\n... (вывод обрезан)"
            return output
        return "Не git-репозиторий"
    except Exception as e:
        return f"Ошибка git diff: {e}"


@register_tool("git_commit", "Создать git commit (с подтверждением)")
def git_commit(message: str, add_all: bool = True) -> str:
    """Создать коммит с указанным сообщением.

    Args:
        message: сообщение коммита
        add_all: добавить все изменения (git add -A)
    """
    if not _confirm_action(f"Git commit: {message[:80]}", category="dangerous"):
        return "❌ Операция отклонена пользователем"

    try:
        if add_all:
            subprocess.run(["git", "add", "-A"], capture_output=True, text=True, timeout=10)

        result = subprocess.run(
            ["git", "commit", "-m", message],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return f"✅ {result.stdout.strip()}"
        else:
            error = result.stderr.strip() or result.stdout.strip()
            return f"❌ Ошибка коммита: {error}"
    except Exception as e:
        return f"Ошибка git commit: {e}"
