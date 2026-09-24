# -*- coding: utf-8 -*-
# core/core.py — BaseAgent(ABC) + ReActEngine
#
# Импортирует _core.py (бывший core.py) напрямую, минуя пакет.
# Импортирует ToolRegistry + register_tool из core/core_tools.py.

import importlib.util
import os
import re
from abc import ABC, abstractmethod
from typing import Optional

# Загружаем _core.py напрямую (он IMMUTABLE, все функции core)
_core_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_core.py")
_spec = importlib.util.spec_from_file_location("_root_core", _core_path)
_root_core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_root_core)

from .core_tools import ToolRegistry, register_tool, get_tool, _GLOBAL_REGISTRY

console = _root_core.console


# ═══════════════════════════════════════════════════════════════════
# ReActEngine
# ═══════════════════════════════════════════════════════════════════

class ReActEngine:
    """
    ReAct-цикл: Thought -> Action -> Observation -> повтор.

    - Вызывает LLM (через _root_core.call_ollama)
    - Парсит теги <call name="..."> для вызова инструментов
    - Передаёт результат инструмента обратно в LLM как Observation
    - Возвращает финальный ответ когда инструменты перестают вызываться
    """

    def __init__(self, tool_registry: Optional[ToolRegistry] = None,
                 max_steps: int = 10,
                 model: str = "qwen2.5-coder:14b"):
        self.tool_registry = tool_registry or _GLOBAL_REGISTRY
        self.max_steps = max_steps
        self.model = model

    def execute(self, system_prompt: str, user_prompt: str) -> str:
        """Запускает ReAct-цикл. Возвращает финальный ответ модели."""
        current_user = user_prompt
        step = 0

        while step < self.max_steps:
            step += 1
            console.print(f"[dim]🤖 ReAct шаг {step}/{self.max_steps}...[/dim]")

            raw = _root_core.call_ollama(system_prompt, current_user,
                                         model_override=self.model)
            if not raw:
                console.print("[red]❌ Пустой ответ от LLM.[/red]")
                return ""

            has_call, result = self._execute_tool_call(raw)

            if has_call:
                current_user = (
                    f"Результат выполнения инструмента:\n{result}\n"
                    "Продолжай выполнение."
                )
                continue

            return raw

        console.print(f"[yellow]⚠️ ReAct-цикл исчерпал лимит шагов ({self.max_steps})[/yellow]")
        return ""

    def _execute_tool_call(self, model_response: str) -> tuple[bool, str]:
        """Ищет <call name="...">...</call> в ответе модели."""
        match = re.search(r'<call name="(\w+)">(.*?)</call>',
                          model_response, re.DOTALL)
        if not match:
            return False, ""

        tool_name = match.group(1)
        raw_args = match.group(2).strip()

        tool_func = self.tool_registry.get(tool_name)
        if not tool_func:
            return True, (f"Ошибка: Инструмент '{tool_name}' "
                          f"не зарегистрирован в реестре.")

        console.print(f"[bold cyan]🔧 Вызов инструмента: "
                      f"{tool_name}({raw_args})[/bold cyan]")

        try:
            if tool_name == "read_file_chunk" and "," in raw_args:
                parts = [p.strip() for p in raw_args.split(",", 2)]
                result = tool_func(parts[0], int(parts[1]), int(parts[2]))
            else:
                result = tool_func(raw_args)

            return True, f"\n<tool_result name=\"{tool_name}\">\n{result}\n</tool_result>\n"
        except Exception as e:
            return True, f"Системный сбой при выполнении инструмента: {e}"


# ═══════════════════════════════════════════════════════════════════
# BaseAgent
# ═══════════════════════════════════════════════════════════════════

class BaseAgent(ABC):
    """
    Базовый класс для всех агентов.

    Предоставляет:
    - ReAct-цикл через ReActEngine
    - Доступ к ToolRegistry
    - run() — абстрактная точка входа
    - call_llm(), load_prompt() — удобные обёртки
    """

    def __init__(self, name: str = "base_agent",
                 tool_registry: Optional[ToolRegistry] = None,
                 max_steps: int = 10,
                 model: str = "qwen2.5-coder:14b"):
        self.name = name
        self.tool_registry = tool_registry or _GLOBAL_REGISTRY
        self.engine = ReActEngine(self.tool_registry, max_steps, model)
        self.model = model

    @abstractmethod
    def run(self):
        """Точка входа агента. Реализуется в наследнике."""
        ...

    def call_llm(self, system_prompt: str, user_prompt: str,
                 model_override: str = None) -> str:
        """Удобная обёртка для вызова LLM через корневой core.py."""
        return _root_core.call_ollama(
            system_prompt, user_prompt,
            model_override or self.model
        )

    def load_prompt(self, role_key: str) -> str:
        """Загружает промпт из prompts.json через корневой core.py."""
        return _root_core.load_prompt_from_file(role_key)

    def run_react(self, system_prompt: str, user_prompt: str) -> str:
        """Запустить ReAct-цикл и вернуть финальный ответ."""
        return self.engine.execute(system_prompt, user_prompt)