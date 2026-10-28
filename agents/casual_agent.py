# -*- coding: utf-8 -*-
# agents/casual_agent.py — CasualAgent(BaseAgent)
#
# Минимальный ReAct-агент для вопросов по коду:
# read_file, list_dir, search, view_file_outline
#
# Фаза 2: принимает model и tracer, интегрирован с TUI

import core
from core import BaseAgent
from modules.settings import settings


_SYSTEM_PROMPT_TEMPLATE = """Ты — полезный ассистент для работы с кодом.

У тебя есть инструменты:
{tools_help}

Отвечай на вопросы пользователя. Если нужно узнать что-то о коде —
используй соответствующий инструмент.

Формат вызова инструмента:
<call name="tool_name">аргументы</call>

Когда получишь результат, проанализируй его и дай ответ пользователю.
"""


class CasualAgent(BaseAgent):
    """
    CasualAgent — базовый ReAct-ассистент для вопросов по коду.

    Использует инструменты: list_dir, view_file_outline, read_file_chunk,
    search_code, git_status, git_diff
    """

    def __init__(self, model: str = None,
                 tracer=None, name: str = "casual_agent",
                 max_steps: int = 15):
        super().__init__(name=name, max_steps=max_steps,
                         model=model or settings.model_coder,
                         tracer=tracer)
        self.tracer = tracer

    def run(self, user_query: str = "") -> str:
        """Точка входа: отвечает на вопрос пользователя."""
        if not user_query:
            user_query = "Чем я могу помочь?"

        tools_help = self.tool_registry.list_tools()
        system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(tools_help=tools_help)

        core.console.print(f"[green]🤖 CasualAgent: {user_query[:100]}...[/green]")

        result = self.run_react(system_prompt, user_query)

        if self.tracer:
            self.tracer.log_final(result)

        return result

    def run_interactive(self, user_query: str,
                        on_message=None) -> str:
        """Интерактивный запуск с callback для сообщений."""
        if not user_query:
            return ""

        tools_help = self.tool_registry.list_tools()
        system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(tools_help=tools_help)

        if on_message:
            on_message("system", "🤔 Думаю...")

        result = self.run_react(system_prompt, user_query)

        if self.tracer:
            self.tracer.log_final(result)

        if on_message:
            on_message("ai", result)

        return result
