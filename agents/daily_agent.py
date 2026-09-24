# -*- coding: utf-8 -*-
# agents/daily_agent.py — DailyAgent(BaseAgent)
#
# Минимальный ReAct-агент для вопросов по коду:
# read_file, list_dir, search, view_file_outline

import core
from core import BaseAgent


_SYSTEM_PROMPT_TEMPLATE = """Ты — полезный ассистент для работы с кодом.

У тебя есть инструменты:
{tools_help}

Отвечай на вопросы пользователя. Если нужно узнать что-то о коде —
используй соответствующий инструмент.

Формат вызова инструмента:
<call name="tool_name">аргументы</call>

Когда получишь результат, проанализируй его и дай ответ пользователю.
"""


class DailyAgent(BaseAgent):
    """
    DailyAgent — базовый ReAct-ассистент для вопросов по коду.

    Использует инструменты: list_dir, view_file_outline, read_file_chunk
    """

    def __init__(self):
        super().__init__(name="daily_agent", max_steps=15)

    def run(self, user_query: str = "") -> str:
        """Точка входа: отвечает на вопрос пользователя."""
        if not user_query:
            user_query = "Чем я могу помочь?"

        tools_help = self.tool_registry.list_tools()
        system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(tools_help=tools_help)

        core.console.print(f"[green]🤖 DailyAgent: {user_query[:100]}...[/green]")

        result = self.run_react(system_prompt, user_query)
        return result