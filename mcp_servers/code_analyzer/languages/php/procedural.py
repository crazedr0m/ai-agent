# -*- coding: utf-8 -*-
# mcp_servers/code_analyzer/languages/php/procedural.py
#
# Процедурный анализатор легаси-кода.
# Анализирует PHP-файлы, не содержащие функций/классов — чистый спагетти-код.
#
# Отличия от PhpAnalyzer:
#   - Не требует tree-sitter (чистый обход AST через ноды)
#   - Собирает top-level statements: echo, include, extract, $_GET и т.д.
#   - Строит граф include-зависимостей
#   - Детектит анти-паттерны (extract(), inline HTML и т.д.)

import os
import re
from collections import Counter

from mcp_servers.code_analyzer.core import _get_all_files, _parse_file


# ── Константы ───────────────────────────────────────────────────────

# Типы нод, которые считаются "процедурными" (top-level statements)
_PROCEDURAL_NODE_TYPES = frozenset({
    "echo_statement",
    "include_expression",
    "include_once_expression",
    "require_expression",
    "require_once_expression",
    "expression_statement",
    "if_statement",
    "while_statement",
    "for_statement",
    "foreach_statement",
    "switch_statement",
    "global_statement",
    "unset_statement",
    "return_statement",
    "assign_left",
    "assign_right",
})

# Регулярки для анти-паттернов
_RE_EXTRACT = re.compile(r"\bextract\s*\(")
_RE_GLOBAL_VAR = re.compile(r"\$_(?:GET|POST|COOKIE|REQUEST|SERVER|SESSION|FILES|ENV)\b")
_RE_JQUERY = re.compile(r"\$\s*\(|\.(?:ready|ajax|get|post|on|click|submit|validate)\(")
_RE_ECHO_HTML = re.compile(r"echo\s*['\"<]")


# ── Основная функция анализа одного файла ───────────────────────────


def analyze_procedural_file(filepath: str) -> dict:
    """Проанализировать процедурный PHP-файл.

    Args:
        filepath: путь к PHP-файлу

    Returns:
        dict с результатами анализа:
          - has_functions: bool (есть ли функции/классы)
          - is_procedural: bool (чисто процедурный)
          - top_level: {node_type: count, ...} — типы top-level statement
          - echo_count: количество echo
          - include_count: количество include/require
          - extract_calls: количество extract() вызовов
          - global_var_access: количество обращений к $_GET/$_POST и т.д.
          - suspected_jquery: количество jQuery-выражений
          - inline_html: есть ли inline HTML вне PHP-тегов
          - antipatterns: список выявленных анти-паттернов
          - character_count: общий размер
    """
    import tree_sitter_php
    from tree_sitter import Language, Parser

    if not os.path.isfile(filepath):
        return {"error": f"Файл не найден: {filepath}"}

    parser = Parser(Language(tree_sitter_php.language_php()))
    parsed = _parse_file(filepath, parser)
    if parsed is None:
        return {"error": f"Не удалось распарсить: {filepath}"}

    root = parsed["root"]
    code = parsed["code"]

    # Собираем статистику по top-level нодам
    node_type_counts: Counter = Counter()
    echo_count = 0
    include_count = 0
    func_count = 0
    class_count = 0
    extract_calls = 0
    global_var_access = 0
    suspected_jquery = 0
    has_inline_html = False
    antipatterns: list[str] = []
    top_level_calls: list[str] = []  # имена вызываемых функций на верхнем уровне
    include_targets: list[str] = []  # файлы, которые инклюдятся

    def walk(node, depth=0):
        nonlocal echo_count, include_count, func_count, class_count
        nonlocal extract_calls, global_var_access, suspected_jquery, has_inline_html

        t = node.type

        # Считаем функции/классы — если они есть, файл не процедурный
        if t == "function_definition":
            func_count += 1
        elif t == "class_declaration":
            class_count += 1

        # Собираем топ-левел статистику (depth 1)
        if depth == 1:
            node_type_counts[t] += 1

            if t == "echo_statement":
                echo_count += 1
                # Текст echo может содержать HTML
                text = code[node.start_byte:node.end_byte]
                if _RE_ECHO_HTML.search(text):
                    has_inline_html = True

            elif t in ("include_expression", "include_once_expression",
                        "require_expression", "require_once_expression"):
                include_count += 1
                # Извлекаем путь
                for child in node.children:
                    if child.type in ("string_embed", "string_literal"):
                        include_targets.append(code[child.start_byte:child.end_byte])

            elif t == "expression_statement":
                # Проверяем содержимое
                text = code[node.start_byte:node.end_byte]

                # Детекция extract()
                if _RE_EXTRACT.search(text):
                    extract_calls += 1
                    if "extract($_GET)" in text or "extract($_POST)" in text:
                        antipatterns.append(
                            "extract($_GET/$_POST) — крайне опасно"
                        )
                    else:
                        antipatterns.append("extract() — потенциально опасно")

                # Детекция глобальных переменных
                gv_matches = _RE_GLOBAL_VAR.findall(text)
                global_var_access += len(gv_matches)

                # Детекция jQuery
                if _RE_JQUERY.search(text):
                    suspected_jquery += 1

        # Обработка inline HTML (текст между PHP-блоками)
        if t == "text" and depth <= 1:
            text = code[node.start_byte:node.end_byte].strip()
            if text and not text.startswith("<?"):
                has_inline_html = True

        for child in node.children:
            walk(child, depth + 1)

    walk(root)

    is_procedural = (func_count == 0 and class_count == 0)

    return {
        "has_functions": func_count > 0 or class_count > 0,
        "is_procedural": is_procedural,
        "func_count": func_count,
        "class_count": class_count,
        "top_level": dict(node_type_counts.most_common(20)),
        "echo_count": echo_count,
        "include_count": include_count,
        "include_targets": include_targets[:20],
        "extract_calls": extract_calls,
        "global_var_access": global_var_access,
        "suspected_jquery": suspected_jquery,
        "has_inline_html": has_inline_html,
        "antipatterns": antipatterns,
        "character_count": len(code),
    }


# ── Сканирование проекта ────────────────────────────────────────────


def scan_procedural_project(project_path: str) -> dict:
    """Сканировать PHP-проект на процедурный код.

    Args:
        project_path: корень проекта

    Returns:
        dict со сводкой:
          - total_php_files: общее число PHP-файлов
          - procedural_count: число чисто процедурных файлов
          - files_with_functions: число файлов с функциями/классами
          - procedural_files: список процедурных файлов с деталями
          - aggregate: агрегированная статистика
    """
    if not os.path.isdir(project_path):
        return {"error": f"Директория не найдена: {project_path}"}

    php_files = _get_all_files(project_path, extension=".php")
    total = len(php_files)
    procedural_files = []
    files_with_funcs = 0

    # Агрегаты
    total_echo = 0
    total_include = 0
    total_extract = 0
    total_global_var = 0
    total_jquery = 0
    files_with_inline_html = 0
    all_antipatterns: Counter = Counter()

    for fp in php_files:
        result = analyze_procedural_file(fp)
        if "error" in result:
            continue

        if result["is_procedural"]:
            procedural_files.append({
                "file": os.path.relpath(fp, project_path),
                "echo_count": result["echo_count"],
                "include_count": result["include_count"],
                "extract_calls": result["extract_calls"],
                "global_var_access": result["global_var_access"],
                "has_inline_html": result["has_inline_html"],
            })
        else:
            files_with_funcs += 1

        total_echo += result["echo_count"]
        total_include += result["include_count"]
        total_extract += result["extract_calls"]
        total_global_var += result["global_var_access"]
        total_jquery += result["suspected_jquery"]
        if result["has_inline_html"]:
            files_with_inline_html += 1
        for ap in result["antipatterns"]:
            all_antipatterns[ap] += 1

    # Сортируем процедурные файлы по размеру (echo_count)
    procedural_files.sort(key=lambda f: f["echo_count"], reverse=True)

    return {
        "total_php_files": total,
        "procedural_count": len(procedural_files),
        "files_with_functions": files_with_funcs,
        "procedural_percent": round(len(procedural_files) / total * 100, 1) if total else 0,
        "procedural_files_top20": procedural_files[:20],
        "aggregate": {
            "total_echo": total_echo,
            "total_include": total_include,
            "total_extract_calls": total_extract,
            "total_global_var_access": total_global_var,
            "total_jquery_usages": total_jquery,
            "files_with_inline_html": files_with_inline_html,
        },
        "antipatterns_summary": dict(all_antipatterns.most_common(10)),
    }