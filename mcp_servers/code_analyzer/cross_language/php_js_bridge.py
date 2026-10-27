# -*- coding: utf-8 -*-
# mcp_servers/code_analyzer/cross_language/php_js_bridge.py
#
# PHP→JS Bridge — кроссязыковый анализ цепочки:
#   PHP (echo/print/строки) → HTML → <script>/inline-JS → .js файлы
#
# Поток:
#   1. Сканируем PHP-файлы через extract_js_from_php_file()
#   2. Извлекаем JS-фрагменты из строковых литералов PHP
#   3. Парсим JS-фрагменты через tree-sitter-javascript для извлечения символов
#   4. Ищем определения этих символов в .js/.ts файлах
#   5. Возвращаем объединённую карту ссылок

import json
import os
import re
from typing import Any

from mcp_servers.code_analyzer.core import _get_all_files, _parse_file
from mcp_servers.code_analyzer.languages import get_analyzer
from mcp_servers.code_analyzer.languages.php.string_detector import extract_js_from_php_file


# ── Извлечение JS-символов из текста ──────────────────────────────

_RE_JS_FUNC_DEF = re.compile(
    r"(?:function\s+(\w+)\s*\()"
    r"|(?:(\w+)\s*[:=]\s*function\s*\()"
    r"|(?:(\w+)\s*[:=]\s*\([^)]*\)\s*=>)"
    r"|(?:const\s+(\w+)\s*[:=])"
    r"|(?:let\s+(\w+)\s*[:=])"
    r"|(?:var\s+(\w+)\s*[:=])"
)
_RE_JS_CALL = re.compile(r"(?:(\w+)\s*\()")


def _extract_js_symbols_from_text(js_text: str) -> dict:
    """Извлечь определения и вызовы JS-символов из текстового фрагмента.

    Returns:
        {"defined": [...], "called": [...]}
    """
    defined = set()
    called = set()

    for match in _RE_JS_FUNC_DEF.finditer(js_text):
        for group in match.groups():
            if group:
                defined.add(group)

    for match in _RE_JS_CALL.finditer(js_text):
        name = match.group(1)
        # Чистим JS-зарезервированные слова
        if name and name not in ("function", "if", "else", "while", "for",
                                 "return", "var", "let", "const", "new",
                                 "typeof", "delete", "this", "switch",
                                 "case", "break", "continue", "try",
                                 "catch", "finally", "throw", "yield",
                                 "async", "await", "import", "export",
                                 "from", "of", "in", "class", "extends"):
            if name not in defined:
                called.add(name)

    return {
        "defined": sorted(defined),
        "called": sorted(called),
    }


# ── Кэш файлов и индекс символов ────────────────────────────────────

_js_file_cache: dict[str, list[str]] = {}  # project_path -> [filepath, ...]
_js_symbol_index: dict[str, dict[str, list[dict]]] = {}  # project_path -> {symbol_name -> [{file, language, signature}, ...]}
_last_project_path: str | None = None


def _is_minified(filename: str) -> bool:
    """Проверить, является ли файл минифицированным (.min.js, .min.ts)."""
    return ".min." in filename


def _build_js_file_list(project_path: str) -> list[str]:
    """Собрать все .js/.ts/.jsx/.tsx файлы проекта (с кэшированием)."""
    global _last_project_path
    if _last_project_path != project_path:
        _js_file_cache.clear()
        _js_symbol_index.clear()
        _last_project_path = project_path

    cache_key = f"{project_path}"
    if cache_key in _js_file_cache:
        return _js_file_cache[cache_key]

    files = []
    for lang in ("javascript", "typescript"):
        ext = ".js" if lang == "javascript" else ".ts"
        jsx_exts = [".jsx", ".tsx"] if lang == "typescript" else [".jsx"]

        lang_files = _get_all_files(project_path, extension=ext)
        lang_files = [f for f in lang_files if not _is_minified(f)]
        files.extend((f, lang) for f in lang_files)

        for jsx_ext in jsx_exts:
            xfiles = _get_all_files(project_path, extension=jsx_ext)
            xfiles = [f for f in xfiles if not _is_minified(f)]
            files.extend((f, lang) for f in xfiles)

    _js_file_cache[cache_key] = files
    return files


def _build_symbol_index(project_path: str) -> dict[str, list[dict]]:
    """Построить индекс всех символов из .js/.ts файлов (с кэшированием).

    Returns:
        {symbol_name: [{file, language, signature}, ...], ...}
    """
    global _last_project_path
    if _last_project_path != project_path:
        _js_file_cache.clear()
        _js_symbol_index.clear()
        _last_project_path = project_path

    cache_key = f"{project_path}"
    if cache_key in _js_symbol_index:
        return _js_symbol_index[cache_key]

    files = _build_js_file_list(project_path)
    index: dict[str, list[dict]] = {}

    for fp, lang in files:
        analyzer = get_analyzer(lang)
        if analyzer is None:
            continue

        # Получаем все определения в файле
        defs = analyzer.collect_definitions(fp)
        for func in defs.get("functions", []):
            name = func.get("name", "")
            if not name:
                continue
            rel = os.path.relpath(fp, project_path)
            entry = {
                "language": lang,
                "file": rel,
                "signature": func,
            }
            index.setdefault(name, []).append(entry)

    _js_symbol_index[cache_key] = index
    return index


# ── Поиск JS-символов в .js файлах ──────────────────────────────────


def find_js_symbol_in_project(
    symbol_name: str,
    project_path: str,
) -> list[dict]:
    """Найти определение символа в .js/.ts файлах проекта (с кэшированием).

    Args:
        symbol_name: имя JS-символа (функция/переменная)
        project_path: корень проекта

    Returns:
        список найденных определений {file, language, signature, ...}
    """
    index = _build_symbol_index(project_path)
    return index.get(symbol_name, [])


# ── Основная функция PHP→JS анализа ────────────────────────────────


def analyze_php_to_js(
    php_file_path: str,
    project_path: str,
) -> dict[str, Any]:
    """Проанализировать PHP-файл на предмет генерации JS-кода.

    Args:
        php_file_path: путь к PHP-файлу
        project_path: корень проекта (для поиска .js файлов)

    Returns:
        dict с результатами анализа:
          - php_file: путь к PHP-файлу
          - generated_js_fragments: список найденных JS-фрагментов в PHP
          - cross_references: связи PHP → JS (символ → где определён в .js)
          - summary: сводка
    """
    if not os.path.isfile(php_file_path):
        return {"error": f"Файл не найден: {php_file_path}"}

    relative_path = os.path.relpath(php_file_path, project_path)

    # Шаг 1: Извлечение JS-фрагментов из PHP
    fragments = extract_js_from_php_file(php_file_path)
    if not fragments:
        return {
            "php_file": relative_path,
            "generated_js_fragments": [],
            "cross_references": [],
            "summary": {
                "js_fragments_found": 0,
                "symbols_defined": 0,
                "symbols_called": 0,
                "resolved_in_js_files": 0,
            },
        }

    # Шаг 2: Извлечение символов из JS-фрагментов
    all_defined = set()
    all_called = set()
    fragment_details = []

    for frag in fragments:
        symbols = _extract_js_symbols_from_text(frag.content)
        all_defined.update(symbols["defined"])
        all_called.update(symbols["called"])
        fragment_details.append({
            "content_preview": frag.content[:120],
            "kind": frag.kind,
            "start_byte": frag.start_byte,
            "end_byte": frag.end_byte,
            "symbols_defined": symbols["defined"],
            "symbols_called": symbols["called"],
        })

    # Шаг 3: Поиск определений в .js/.ts файлах
    cross_refs = []
    resolved_symbols = set()

    for symbol in sorted(all_defined | all_called):
        definitions = find_js_symbol_in_project(symbol, project_path)
        if definitions:
            resolved_symbols.add(symbol)
        cross_refs.append({
            "symbol": symbol,
            "origin": "defined_in_php_string" if symbol in all_defined else "called_from_php_string",
            "resolved": len(definitions) > 0,
            "definitions": definitions[:5],  # ограничиваем
        })

    return {
        "php_file": relative_path,
        "generated_js_fragments": fragment_details,
        "cross_references": cross_refs,
        "summary": {
            "js_fragments_found": len(fragments),
            "symbols_defined": len(all_defined),
            "symbols_called": len(all_called),
            "resolved_in_js_files": len(resolved_symbols),
        },
    }


def scan_project_php_to_js(
    project_path: str,
) -> list[dict[str, Any]]:
    """Сканировать весь проект на PHP→JS связи.

    Args:
        project_path: корень проекта

    Returns:
        список результатов для каждого PHP-файла, содержащего JS
    """
    if not os.path.isdir(project_path):
        return [{"error": f"Директория не найдена: {project_path}"}]

    php_files = _get_all_files(project_path, extension=".php")
    results = []

    for php_file in php_files:
        result = analyze_php_to_js(php_file, project_path)
        if result.get("generated_js_fragments"):
            results.append(result)

    return results