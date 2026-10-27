# -*- coding: utf-8 -*-
# mcp_servers/filesystem/helpers.py — Вспомогательные функции filesystem-сервера


def should_skip_dir(dirname: str) -> bool:
    """Проверить, нужно ли пропустить директорию при обходе.

    Args:
        dirname: имя директории для проверки.

    Returns:
        True, если директорию нужно пропустить.
    """
    return dirname in ("venv", ".git", "__pycache__", ".pytest_cache", "node_modules")