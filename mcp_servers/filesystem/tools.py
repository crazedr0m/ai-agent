# -*- coding: utf-8 -*-
# mcp_servers/filesystem/tools.py — Инструменты filesystem-сервера
#
# 6 инструментов:
#   - read_file       — чтение диапазона строк из файла
#   - write_file      — запись содержимого в файл (полная перезапись)
#   - list_dir        — содержимое папки
#   - search_files    — поиск файлов по glob-паттерну
#   - stat_file       — информация о файле/папке
#   - grep_code       — поиск по содержимому файлов (grep)

import os
import re
import fnmatch

from mcp_servers.filesystem.server import mcp
from mcp_servers.filesystem.helpers import should_skip_dir


@mcp.tool()
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
            return (
                f"[пусто] Файл {file_path} не содержит строк "
                f"в диапазоне {start_line}-{end_line}"
            )
        return "\n".join(lines)
    except FileNotFoundError:
        return f"Ошибка: файл '{file_path}' не найден"
    except Exception as e:
        return f"Ошибка чтения файла: {e}"


@mcp.tool()
def write_file(file_path: str, content: str) -> str:
    """Записать содержимое в файл (полная перезапись).

    Args:
        file_path: путь к файлу
        content: новое содержимое файла
    """
    try:
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"✅ Файл {file_path} записан ({len(content)} символов)"
    except Exception as e:
        return f"Ошибка записи файла: {e}"


@mcp.tool()
def list_dir(path: str = ".") -> str:
    """Показать содержимое папки.

    Args:
        path: путь к папке
    """
    try:
        entries = os.listdir(path)
        if not entries:
            return "[пусто]"
        lines = []
        for entry in sorted(entries):
            full = os.path.join(path, entry)
            if os.path.isdir(full):
                lines.append(f"📁 {entry}/")
            elif os.path.isfile(full):
                size = os.path.getsize(full)
                lines.append(f"📄 {entry} ({size} B)")
            else:
                lines.append(f"🔗 {entry}")
        return "\n".join(lines)
    except Exception as e:
        return f"Ошибка чтения папки: {e}"


@mcp.tool()
def search_files(pattern: str, path: str = ".", file_pattern: str = "*") -> str:
    """Поиск файлов по имени (glob).

    Args:
        pattern: glob-паттерн для поиска (например *.py, test_*)
        path: директория для поиска
        file_pattern: дополнительный фильтр по расширению
    """
    results = []
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if not should_skip_dir(d)]
        for f in files:
            if not fnmatch.fnmatch(f, pattern):
                continue
            if file_pattern != "*" and not fnmatch.fnmatch(f, file_pattern):
                continue
            rel = os.path.relpath(os.path.join(root, f), path)
            results.append(rel)
    if not results:
        return "Совпадений не найдено"
    return "\n".join(sorted(results)[:200])


@mcp.tool()
def stat_file(file_path: str) -> str:
    """Показать информацию о файле или папке.

    Args:
        file_path: путь к файлу или папке
    """
    try:
        st = os.stat(file_path)
        import datetime
        info = []
        if os.path.isdir(file_path):
            info.append(f"📁 Папка: {file_path}")
        elif os.path.isfile(file_path):
            info.append(f"📄 Файл: {file_path}")
        else:
            info.append(f"🔗 {file_path}")
        info.append(f"Размер: {st.st_size} B")
        info.append(
            f"Изменён: {datetime.datetime.fromtimestamp(st.st_mtime).isoformat()}"
        )
        info.append(
            f"Создан: {datetime.datetime.fromtimestamp(st.st_ctime).isoformat()}"
        )
        return "\n".join(info)
    except Exception as e:
        return f"Ошибка: {e}"


@mcp.tool()
def grep_code(pattern: str, path: str = ".", file_pattern: str = "*.py") -> str:
    """Поиск по содержимому файлов (grep).

    Args:
        pattern: регулярное выражение для поиска
        path: директория для поиска
        file_pattern: glob-паттерн для файлов (по умолчанию *.py)
    """
    results = []
    try:
        regex = re.compile(pattern)
    except re.error as e:
        return f"Ошибка в регулярном выражении: {e}"

    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if not should_skip_dir(d)]
        for f in files:
            if not fnmatch.fnmatch(f, file_pattern):
                continue
            filepath = os.path.join(root, f)
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as fh:
                    for i, line in enumerate(fh, 1):
                        if regex.search(line):
                            rel = os.path.relpath(filepath, path)
                            results.append(f"{rel}:{i}:{line.rstrip()[:200]}")
            except Exception:
                pass

    if not results:
        return "Совпадений не найдено"
    output = "\n".join(results[:100])
    if len(results) > 100:
        output += f"\n... и ещё {len(results) - 100} совпадений"
    return output