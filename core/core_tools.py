# -*- coding: utf-8 -*-
# core/core_tools.py — ToolRegistry + @register_tool декоратор
#
# Содержит реестр инструментов и декоратор для регистрации.
# Импортируется из core/core.py и из агентов.

from typing import Optional, Callable


class ToolRegistry:
    """Реестр инструментов с поддержкой декоратора @register_tool."""

    def __init__(self):
        self._tools: dict[str, dict] = {}

    def register(self, name: str, description: str = "",
                 func: Optional[Callable] = None) -> Callable:
        """Регистрирует инструмент. Работает и как декоратор, и как обычный вызов."""
        if func is not None:
            self._tools[name] = {"func": func, "description": description}
            return func

        def decorator(f):
            self._tools[name] = {"func": f, "description": description}
            return f
        return decorator

    def get(self, name: str) -> Optional[Callable]:
        entry = self._tools.get(name)
        return entry["func"] if entry else None

    def list_tools(self) -> str:
        """Возвращает описание инструментов для вставки в system prompt."""
        lines = []
        for name, info in self._tools.items():
            lines.append(f"- {name}: {info['description']}")
        return "\n".join(lines)

    @property
    def tool_names(self):
        return list(self._tools.keys())

    def __len__(self):
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools


# Глобальный реестр (singleton-like)
_GLOBAL_REGISTRY = ToolRegistry()


def register_tool(name: str, description: str = ""):
    """Декоратор для регистрации инструментов в глобальном реестре.

    Пример:
        @register_tool("list_dir", "Показать содержимое папки")
        def list_dir(path: str) -> str: ...
    """
    return _GLOBAL_REGISTRY.register(name, description)


def get_tool(name: str) -> Optional[Callable]:
    """Получить функцию инструмента по имени из глобального реестра."""
    return _GLOBAL_REGISTRY.get(name)