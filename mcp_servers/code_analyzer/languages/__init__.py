# -*- coding: utf-8 -*-
# mcp_servers/code_analyzer/languages/__init__.py — Реестр языковых анализаторов
#
# ParserRegistry — фабрика/реестр: get("python") → PythonAnalyzer

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp_servers.code_analyzer.languages.base import BaseAnalyzer

_registry: dict[str, type["BaseAnalyzer"]] = {}


def register(language: str, analyzer_cls: type["BaseAnalyzer"]):
    """Зарегистрировать класс анализатора для языка."""
    _registry[language] = analyzer_cls


def get_analyzer(language: str) -> "BaseAnalyzer | None":
    """Получить экземпляр анализатора для языка (singleton per process)."""
    cls = _registry.get(language)
    if cls is None:
        return None
    return cls()


def get_supported_languages() -> list[str]:
    """Список зарегистрированных языков."""
    return list(_registry.keys())


def infer_language(file_path: str) -> str | None:
    """Определить язык по расширению файла."""
    ext_map = {
        ".py": "python",
        ".php": "php",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".go": "go",
    }
    _, ext = __import__("os").path.splitext(file_path)
    return ext_map.get(ext.lower())


# Импортируем анализаторы, чтобы они зарегистрировались
# (каждый импорт выполняет register() на уровне модуля)
import mcp_servers.code_analyzer.languages.python.analyzer  # noqa: F401, E402

import mcp_servers.code_analyzer.languages.php.analyzer  # noqa: F401, E402

import mcp_servers.code_analyzer.languages.javascript.analyzer  # noqa: F401, E402

import mcp_servers.code_analyzer.languages.typescript.analyzer  # noqa: F401, E402

import mcp_servers.code_analyzer.languages.go.analyzer  # noqa: F401, E402