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

    max_steps: настраиваемый лимит шагов (по умолчанию 10, может быть задан через манифест)
    
    ✅ Улучшение №1: max_steps теперь настраивается через migration_manifest.json
    """

    def __init__(self, tool_registry: Optional[ToolRegistry] = None,
                 max_steps: int = 10,
                 model: str = "qwen2.5-coder:14b",
                 tracer=None):
        self.tool_registry = tool_registry or _GLOBAL_REGISTRY
        self.max_steps = max_steps
        self.model = model
        self.tracer = tracer

    def _log(self, step_type: str, content: str, metadata: dict = None):
        """Записать шаг в трейс, если tracer подключён."""
        if not self.tracer:
            return
        from modules.tracer import StepTrace
        self.tracer.log_step(StepTrace(step_type, content, metadata or {}))

    def execute(self, system_prompt: str, user_prompt: str) -> str:
        """Запускает ReAct-цикл. Возвращает финальный ответ модели.

        Фаза 1.5: Repair-цикл — невалидный вызов (неверные аргументы,
        отсутствующие обязательные параметры) возвращается модели
        с точным описанием ошибки для исправления. До 2 retry на шаг.

        История диалога накапливается: каждый шаг видит исходную задачу
        и все предыдущие наблюдения.
        """
        history = [user_prompt]
        step = 0

        while step < self.max_steps:
            step += 1
            console.print(f"[dim]🤖 ReAct шаг {step}/{self.max_steps}...[/dim]")

            current_user = "\n\n".join(history)
            raw = _root_core.call_ollama(system_prompt, current_user,
                                         model_override=self.model)
            if not raw:
                console.print("[red]❌ Пустой ответ от LLM.[/red]")
                return ""

            self._log("llm_call", raw, {"model": self.model, "step": step})

            has_call, result = self.execute_tool_call(raw)

            if not has_call:
                # Нет вызова — финальный ответ
                return raw

            # Repair-цикл (Фаза 1.5): проверяем, что вызов был успешным
            # execute_tool_call возвращает <tool_result> при успехе
            # или сообщение об ошибке при провале.
            result_text = result.strip()
            if result_text.startswith("<tool_result"):
                # Успешный вызов — передаём результат обратно модели
                history.append(
                    f"Результат выполнения инструмента:\n{result}\n"
                    "Продолжай выполнение."
                )
                continue

            # Ошибка (неизвестный инструмент, сбой) — repair
            console.print(f"[yellow]⚠️ Repair: {result_text[:100]}[/yellow]")

            # До 2 попыток исправить
            repaired = False
            for repair_attempt in range(2):
                repair_prompt = (
                    f"Произошла ошибка при выполнении вызова:\n"
                    f"{result_text}\n\n"
                    f"Пожалуйста, исправь вызов и повтори. "
                    f"Убедись, что все обязательные параметры указаны "
                    f"с правильными типами."
                )
                raw2 = _root_core.call_ollama(
                    system_prompt, repair_prompt,
                    model_override=self.model)
                if not raw2:
                    break

                self._log("llm_call", raw2,
                          {"model": self.model, "step": step,
                           "repair_attempt": repair_attempt + 1})

                has_call2, result2 = self.execute_tool_call(raw2)
                if has_call2 and result2.strip().startswith("<tool_result"):
                    history.append(
                        f"Результат выполнения инструмента:\n{result2}\n"
                        "Продолжай выполнение."
                    )
                    repaired = True
                    break
                result_text = result2

            if repaired:
                continue

            # Repair не удался — отдаём ошибку модели и продолжаем
            history.append(
                f"Не удалось выполнить вызов. Ошибка: {result_text}\n"
                "Продолжай выполнение без этого инструмента."
            )

        console.print(f"[yellow]⚠️ ReAct-цикл исчерпал лимит шагов ({self.max_steps})[/yellow]")
        return ""

    def execute_tool_call(self, model_response: str) -> tuple[bool, str]:
        """Ищет <call name="...">...</call> в ответе модели.

        Фаза 1.3: использует validate_call() для парсинга аргументов по JSON Schema.
        Фаза 1.4: использует tool_parser.parse_tool_call() для мультиформатного парсинга.
        """
        from modules.tool_parser import parse_tool_call

        parsed = parse_tool_call(model_response)
        if parsed is None:
            return False, ""

        tool_name, parsed_args = parsed

        tool_func = self.tool_registry.get(tool_name)
        if not tool_func:
            self._log("tool_call", parsed_args,
                      {"tool_name": tool_name, "args": parsed_args})
            self._log("tool_result", f"Инструмент '{tool_name}' не зарегистрирован",
                      {"tool_name": tool_name, "error": True})
            return True, (f"Ошибка: Инструмент '{tool_name}' "
                          f"не зарегистрирован в реестре.")

        # Валидация аргументов по схеме (Фаза 1.3)
        is_valid, kwargs, error = self.tool_registry.validate_call(
            tool_name, parsed_args)

        console.print(f"[bold cyan]🔧 Вызов инструмента: "
                      f"{tool_name}({kwargs})[/bold cyan]")

        self._log("tool_call", parsed_args,
                  {"tool_name": tool_name, "args": parsed_args,
                   "kwargs": kwargs})

        if not is_valid:
            # Невалидные аргументы — возвращаем ошибку, чтобы сработал repair
            self._log("tool_result", error,
                      {"tool_name": tool_name, "error": True})
            return True, f"Ошибка вызова '{tool_name}': {error}"

        try:
            result = tool_func(**kwargs)

            self._log("tool_result", str(result),
                      {"tool_name": tool_name})
            return True, f"\n<tool_result name=\"{tool_name}\">\n{result}\n</tool_result>\n"
        except Exception as e:
            self._log("tool_result", str(e),
                      {"tool_name": tool_name, "error": True})
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

    max_steps: настраиваемый лимит шагов (по умолчанию 10, может быть задан через манифест)
    
    ✅ Улучшение №1: max_steps теперь настраивается через migration_manifest.json
    
    🔄 Улучшение №2: MigrationAgent поддерживает параллельное выполнение задач через asyncio.gather()
    """

    def __init__(self, name: str = "base_agent",
                 tool_registry: Optional[ToolRegistry] = None,
                 max_steps: int = 10,
                 model: str = "qwen2.5-coder:14b",
                 tracer=None):
        self.name = name
        self.tool_registry = tool_registry or _GLOBAL_REGISTRY
        self.tracer = tracer
        self.engine = ReActEngine(self.tool_registry, max_steps, model, tracer)
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