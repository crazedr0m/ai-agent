# -*- coding: utf-8 -*-
# mcp_servers/code_analyzer/core.py — Ядро: кэш AST, файловый воркер, утилиты
#
# Не имеет знания о конкретных языках. Только инфраструктура:
#   - AST cache (один на весь сервер)
#   - _parse_file, _get_text, _get_all_files, _clear_cache
#
# Используется языковыми модулями (languages/*/analyzer.py) через ParserRegistry.

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tree_sitter import Node


# ── AST-кэш ────────────────────────────────────────────────────────
_ast_cache: dict[str, dict] = {}


def _get_text(node: "Node", code: str) -> str:
    """Извлечь текст узла AST из исходного кода."""
    return code[node.start_byte : node.end_byte]


def _parse_file(filepath: str, parser) -> dict | None:
    """Распарсить файл, вернуть AST-структуру (с кэшированием).

    Args:
        filepath: путь к файлу
        parser: tree-sitter Parser для нужного языка

    Returns:
        dict с ключами tree, code, root — или None при ошибке
    """
    if filepath in _ast_cache:
        return _ast_cache[filepath]

    if not os.path.isfile(filepath):
        return None

    try:
        with open(filepath, "rb") as f:
            code = f.read()
    except Exception:
        return None

    tree = parser.parse(code)
    _ast_cache[filepath] = {
        "tree": tree,
        "code": code.decode("utf-8", errors="replace"),
        "root": tree.root_node,
    }
    return _ast_cache[filepath]


def _clear_cache():
    """Сбросить кэш AST (для тестов и принудительного пересканирования)."""
    _ast_cache.clear()


def _get_all_files(root_path: str, extension: str = ".py") -> list[str]:
    """Рекурсивно найти все файлы с заданным расширением в директории.

    Пропускает venv, __pycache__, .git, node_modules и скрытые папки.

    Args:
        root_path: корневая директория
        extension: расширение файла (например ".php", ".js")

    Returns:
        отсортированный список полных путей
    """
    files = []
    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = [
            d
            for d in dirnames
            if not d.startswith(".")
            and d not in ("venv", "__pycache__", "node_modules", "vendor")
        ]
        for f in filenames:
            if f.endswith(extension):
                files.append(os.path.join(dirpath, f))
    return sorted(files)