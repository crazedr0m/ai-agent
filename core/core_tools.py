# -*- coding: utf-8 -*-
# core/core_tools.py — ToolRegistry + @register_tool декоратор
#
# Содержит реестр инструментов и декоратор для регистрации.
# Импортируется из core/core.py и из агентов.
#
# Фаза 1.3: JSON Schema генерируется из type hints автоматически.
# Валидация: validate_call() преобразует сырой аргумент в kwargs.

import inspect
import typing
from typing import Any, Callable, Optional


# ──────────────────────────────────────────────
# Утилиты для JSON Schema
# ──────────────────────────────────────────────

_PYTHON_TO_JSON_SCHEMA = {
    str: {"type": "string"},
    int: {"type": "integer"},
    float: {"type": "number"},
    bool: {"type": "boolean"},
    Any: {},
    type(None): {"type": "null"},
}


def _type_to_schema(annotation: Any) -> dict:
    """Преобразовать аннотацию типа Python в JSON Schema."""
    origin = typing.get_origin(annotation)
    args = typing.get_args(annotation)

    if origin is list:
        item_schema = _type_to_schema(args[0]) if args else {}
        return {"type": "array", "items": item_schema}
    if origin is dict:
        return {"type": "object"}
    if origin is Optional:
        inner = _type_to_schema(args[0]) if args else {}
        return {**inner, "nullable": True}

    return _PYTHON_TO_JSON_SCHEMA.get(annotation, {})


def _func_to_schema(func: Callable) -> dict:
    """Сгенерировать JSON Schema для функции по её сигнатуре.

    Возвращает {"type": "object", "properties": {...}, "required": [...]}
    """
    sig = inspect.signature(func)
    hints = typing.get_type_hints(func)

    properties = {}
    required = []

    for name, param in sig.parameters.items():
        if name == "return":
            continue
        annotation = hints.get(name, str)
        schema_entry = _type_to_schema(annotation)
        if param.default is inspect.Parameter.empty:
            required.append(name)
        else:
            schema_entry["default"] = param.default
        schema_entry.setdefault("description", name)
        properties[name] = schema_entry

    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


# ──────────────────────────────────────────────
# Парсинг сырых аргументов
# ──────────────────────────────────────────────


def _parse_raw_args(raw: str, schema: dict) -> dict:
    """Парсит сырую строку аргументов в dict для передачи в функцию.

    Пробует последовательно:
    1. JSON object
    2. key=value, key=value (Python-стиль)
    3. Позиционные аргументы (по порядку параметров из схемы)
    """
    if not raw or not schema:
        return {}

    import re

    raw = raw.strip()

    # 1. JSON object
    if raw.startswith("{") and raw.endswith("}"):
        try:
            import json
            return json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            pass

    # 2. key=value, key=value (Python-стиль)
    # Покрывает: path="agents", file_path="test_core.py", start_line=10
    # А также: path='agents' и голые значения без кавычек
    kwargs = {}

    # Разбиваем по запятым, уважая кавычки
    pairs = _split_respecting_quotes(raw)
    named_count = 0

    for pair in pairs:
        pair = pair.strip()
        eq_match = re.match(r'(\w+)\s*=\s*(.+)', pair)
        if eq_match:
            key = eq_match.group(1)
            val = eq_match.group(2).strip()
            val = _unquote(val)
            kwargs[key] = _coerce_type(val, schema, key)
            named_count += 1

    if named_count > 0 and named_count == len(pairs):
        return kwargs

    # 3. Позиционные аргументы
    props = schema.get("properties", {})
    param_names = list(props.keys())
    if not param_names:
        return {}

    # Если после неудачного key=value остались позиционные — используем их
    if named_count == 0:
        values = [_unquote(p.strip()) for p in pairs]
        result = {}
        for i, val in enumerate(values):
            if i < len(param_names):
                result[param_names[i]] = _coerce_type(val, schema, param_names[i])
        return result

    return kwargs


def _split_respecting_quotes(text: str) -> list[str]:
    """Разбить строку по запятым, игнорируя запятые внутри кавычек."""
    parts = []
    current = []
    in_quote = None
    for ch in text:
        if ch in ('"', "'"):
            if in_quote is None:
                in_quote = ch
            elif ch == in_quote:
                in_quote = None
            current.append(ch)
        elif ch == ',' and in_quote is None:
            parts.append(''.join(current))
            current = []
        else:
            current.append(ch)
    parts.append(''.join(current))
    return parts


def _unquote(val: str) -> str:
    """Снять кавычки со строки."""
    if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
        return val[1:-1]
    return val


def _coerce_type(val: str, schema: dict, param_name: str) -> Any:
    """Привести значение к нужному типу по схеме."""
    props = schema.get("properties", {})
    param_schema = props.get(param_name, {})
    param_type = param_schema.get("type")

    if param_type == "integer":
        try:
            return int(val)
        except (ValueError, TypeError):
            return val
    if param_type == "number":
        try:
            return float(val)
        except (ValueError, TypeError):
            return val
    return val


# ──────────────────────────────────────────────
# ToolRegistry
# ──────────────────────────────────────────────


class ToolRegistry:
    """Реестр инструментов с поддержкой JSON Schema + валидации.

    Каждый инструмент хранит:
    - func: Callable
    - description: str
    - parameters: dict (JSON Schema object)
    """

    def __init__(self):
        self._tools: dict[str, dict] = {}

    def register(self, name: str, description: str = "",
                 func: Optional[Callable] = None) -> Callable:
        """Регистрирует инструмент. Работает и как декоратор, и как вызов.

        JSON Schema генерируется автоматически из type hints функции.
        """
        def _register(f):
            parameters = _func_to_schema(f)
            self._tools[name] = {
                "func": f,
                "description": description,
                "parameters": parameters,
            }
            return f

        if func is not None:
            return _register(func)

        return _register

    def get(self, name: str) -> Optional[Callable]:
        entry = self._tools.get(name)
        return entry["func"] if entry else None

    def get_schema(self, name: str) -> Optional[dict]:
        """Получить JSON Schema параметров инструмента."""
        entry = self._tools.get(name)
        if not entry:
            return None
        return entry.get("parameters", {})

    def validate_call(self, name: str, raw_args: str) -> tuple[bool, dict, str]:
        """Распарсить и валидировать сырые аргументы по схеме инструмента.

        Возвращает (is_valid, kwargs, error_message).
        """
        entry = self._tools.get(name)
        if not entry:
            return False, {}, f"Инструмент '{name}' не зарегистрирован"

        schema = entry.get("parameters", {})
        required = schema.get("required", [])
        properties = schema.get("properties", {})

        if not raw_args:
            if required:
                return False, {}, f"Требуются аргументы: {', '.join(required)}"
            return True, {}, ""

        parsed = _parse_raw_args(raw_args, schema)

        # Проверяем обязательные параметры
        missing = [p for p in required if p not in parsed]
        if missing:
            return False, parsed, f"Отсутствуют обязательные параметры: {', '.join(missing)}"

        # Подставляем значения по умолчанию для отсутствующих optional
        for pname, pdef in properties.items():
            if pname not in parsed and "default" in pdef:
                parsed[pname] = pdef["default"]

        return True, parsed, ""

    def list_tools(self) -> str:
        """Возвращает описание инструментов для вставки в system prompt."""
        lines = []
        for name, info in self._tools.items():
            params = info.get("parameters", {})
            props = params.get("properties", {})
            args_info = ", ".join(
                f"{n}: {p.get('type', 'str')}"
                for n, p in props.items()
            )
            lines.append(f"- {name}({args_info}): {info['description']}")
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