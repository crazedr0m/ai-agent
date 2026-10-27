# -*- coding: utf-8 -*-
# mcp_servers/code_analyzer/languages/base.py — Базовый класс языкового анализатора
#
# Все языковые анализаторы (Python, PHP, JS, TS, Go) наследуют BaseAnalyzer.

from abc import ABC, abstractmethod
from tree_sitter import Language, Parser


class BaseAnalyzer(ABC):
    """Абстрактный анализатор для одного языка программирования.

    Каждый подкласс определяет:
    - language — строковый идентификатор (например "python", "php")
    - language_lib — tree-sitter language library (tree_sitter_python.language())
    - _node_types — маппинг концепций на AST-типы нод

    Потомок должен переопределить:
    - collect_definitions(filepath) → dict
    - get_symbol_signature(filepath, symbol_name) → dict | None
    - build_call_graph(filepath) → dict[str, list[str]]
    """

    language: str = ""
    """Строковый идентификатор языка (например "python")."""

    @property
    @abstractmethod
    def language_lib(self):
        """tree-sitter Language object (tree_sitter_python.language())."""

    def __init__(self):
        self._parser = Parser(Language(self.language_lib()))

    @property
    def parser(self) -> Parser:
        return self._parser

    # ── Специфичные для языка маппинги AST-нод ─────────────────────
    # Подклассы переопределяют эти константы

    # Типы нод для определения функций
    function_node_type: str = "function_definition"
    method_node_type: str = "method_definition"

    # Типы нод для классов
    class_node_type: str = "class_definition"
    interface_node_type: str | None = None  # TS-only

    # Типы нод для вызовов
    call_node_type: str = "call"

    # Типы нод для импортов
    import_node_types: tuple[str, ...] = ("import_statement", "import_from_statement")

    # Поле для имени функции/класса
    name_field: str = "name"
    name_field_alt: str | None = None  # fallback если name на другом поле

    # ── Интерфейс ──────────────────────────────────────────────────

    @abstractmethod
    def collect_definitions(self, filepath: str) -> dict:
        """Собрать все функции, классы, импорты, вызовы из файла.

        Returns:
            {"functions": [...], "classes": [...], "imports": [...], "calls": [...]}
        """

    @abstractmethod
    def get_symbol_signature(self, filepath: str, symbol_name: str) -> dict | None:
        """Извлечь сигнатуру символа: имя, параметры, return_type, docstring."""

    @abstractmethod
    def build_call_graph(self, filepath: str) -> dict[str, list[str]]:
        """Построить граф вызовов: {caller: [callee, ...]}."""