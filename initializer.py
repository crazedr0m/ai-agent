# -*- coding: utf-8 -*-
# initializer.py — Тонкая обёртка → MigrationAgent
#
# Сохранена точка входа для совместимости со старыми импортами.
# Основная логика в agents/migration_agent.py

from agents.migration_agent import MigrationAgent


def generate_migration_plan() -> bool:
    """Генерирует tasks.json через MigrationAgent (точка входа для agent.py)."""
    agent = MigrationAgent()
    return agent.generate_plan()
