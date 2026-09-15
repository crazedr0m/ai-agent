# core_tools.py
import os
import sqlite3 # или psycopg2 / sqlalchemy в зависимости от БД

def list_dir(path: str) -> str:
    """Аналог ls: возвращает список файлов в папке."""
    try:
        return "\n".join(os.listdir(path))
    except Exception as e:
        return f"Ошибка чтения папки: {e}"

def view_file_outline(file_path: str) -> str:
    """Сканирует файл на 1100+ строк и вытаскивает ТОЛЬКО сигнатуры функций и классов."""
    try:
        outline = []
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f, 1):
                stripped = line.strip()
                if stripped.startswith(("def ", "class ", "async def ")):
                    outline.append(f"Строка {i}: {stripped}")
        return "\n".join(outline) if outline else "Функции и классы не найдены."
    except Exception as e:
        return f"Ошибка анализа структуры файла: {e}"

def read_file_chunk(file_path: str, start_line: int, end_line: int) -> str:
    """Аналог cat с лимитом: читает строго определенный диапазон строк большого файла."""
    try:
        lines_to_return = []
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f, 1):
                if start_line <= i <= end_line:
                    lines_to_return.append(f"{i}: {line.rstrip()}")
                if i > end_line:
                    break
        return "\n".join(lines_to_return)
    except Exception as e:
        return f"Ошибка чтения файла: {e}"

def query_db_schema(db_path: str) -> str:
    """Показывает структуру таблиц в базе данных (пример для SQLite)."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        conn.close()
        return "\n\n".join([f"Таблица: {name}\nСхема: {sql}" for name, sql in tables])
    except Exception as e:
        return f"Ошибка чтения схемы БД: {e}"

# Карта доступных инструментов
TOOLS_MAP = {
    "list_dir": list_dir,
    "view_file_outline": view_file_outline,
    "read_file_chunk": read_file_chunk,
    "query_db_schema": query_db_schema
}
