# -*- coding: utf-8 -*-
# agent.py — Точка входа
import os
import sys
import json
from rich.panel import Panel

import core
from agents.migration_agent import MigrationAgent

if __name__ == "__main__":
    core.console.print(Panel.fit("[bold green]🌟 AUTONOMOUS AI SOFTWARE ENGINEER v1.0 🌟[/bold green]", border_style="green"))

    agent = MigrationAgent()
    agent.run()
