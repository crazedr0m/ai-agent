# -*- coding: utf-8 -*-
# agent.py — Единая точка входа (Фаза 2 + Фаза 3)
#
# Подкоманды:
#   agent chat [--model M]    — TUI-чат с CasualAgent
#   agent migrate             — конвейер миграции (MigrationAgent)
#   agent trace [list|show N] — просмотр трейсов
#   agent tools               — список зарегистрированных инструментов
#   agent mcp [connect]       — управление MCP-серверами
#
# Флаги:
#   --model, -m    — модель для chat (по умолчанию из model_profiles.json)
#   --session, -s  — ID сессии для возобновления

import argparse
import os
import sys
import json
from datetime import datetime

import core
from core import BaseAgent

# Регистрируем все инструменты (включая dev_tools из Фазы 2)
import core_tools  # noqa: F401

# Подключаем MCP-серверы (Фаза 3)
from modules.mcp_client import connect_mcp_servers
_ = connect_mcp_servers()  # noqa: регистрирует MCP-инструменты


def cmd_chat(args: argparse.Namespace):
    """Запустить TUI-чат с CasualAgent."""
    from modules.tui.app import TUIApp

    model = args.model or "qwen2.5-coder:14b"
    session_id = args.session

    core.console.print(f"[bold green]💬 Чат-режим (модель: {model})[/bold green]")

    # Создаём TUI
    app = TUIApp(width=120, height=30)

    # Создаём CasualAgent с трейсером
    from modules.tracer import TraceSession
    tracer = TraceSession("casual_agent")
    from agents.casual_agent import CasualAgent
    agent = CasualAgent(model=model, tracer=tracer)

    # Привязываем события TUI → агент
    app.on_new_message = lambda msg: None  # будет обрабатываться через цикл

    # Загружаем историю сессии если есть
    if session_id:
        _load_session_history(app, session_id)

    app.add_chat_message("system", f"🤖 CasualAgent запущен (модель: {model})")
    app.add_chat_message("system", "Задай вопрос о коде. Доступны инструменты: read, search, list_dir, git.")

    # Запускаем TUI
    app.run(agent=agent, tracer=tracer)


def cmd_migrate(args: argparse.Namespace):
    """Запустить конвейер миграции."""
    from agents.migration_agent import MigrationAgent

    core.console.print("[bold green]🚀 Режим миграции[/bold green]")

    from modules.tracer import TraceSession
    tracer = TraceSession("migration_agent")
    agent = MigrationAgent(tracer=tracer)
    agent.run()


def cmd_trace(args: argparse.Namespace):
    """Просмотр трейсов."""
    traces_dir = "traces"

    if not os.path.exists(traces_dir):
        core.console.print("[yellow]📭 Директория трейсов не найдена.[/yellow]")
        return

    sessions = sorted([
        d for d in os.listdir(traces_dir)
        if d.startswith("session_")
    ], reverse=True)

    if not sessions:
        core.console.print("[yellow]📭 Нет сохранённых сессий.[/yellow]")
        return

    if args.action == "list":
        core.console.print("[bold cyan]📋 Сессии трейсов:[/bold cyan]")
        for i, s in enumerate(sessions[:20], 1):
            session_dir = os.path.join(traces_dir, s)
            jsonl_path = os.path.join(session_dir, "trace.jsonl")
            step_count = 0
            if os.path.exists(jsonl_path):
                with open(jsonl_path) as f:
                    step_count = sum(1 for _ in f)
            core.console.print(f"  {i}. {s} ({step_count} записей)")

    elif args.action == "show":
        try:
            idx = int(args.n) - 1 if args.n else 0
            if idx < 0 or idx >= len(sessions):
                core.console.print(f"[red]❌ Неверный индекс. Доступно: 1-{len(sessions)}[/red]")
                return
            session_name = sessions[idx]
            session_dir = os.path.join(traces_dir, session_name)
            jsonl_path = os.path.join(session_dir, "trace.jsonl")

            if not os.path.exists(jsonl_path):
                core.console.print(f"[red]❌ Файл трейса не найден: {jsonl_path}[/red]")
                return

            core.console.print(f"[bold cyan]📄 Сессия: {session_name}[/bold cyan]")
            with open(jsonl_path) as f:
                for line in f:
                    record = json.loads(line)
                    _print_trace_record(record)
        except (ValueError, IndexError):
            core.console.print("[red]❌ Укажите номер сессии из списка.[/red]")


def _print_trace_record(record: dict):
    """Вывести одну запись трейса в читаемом виде."""
    t = record.get("type", "unknown")
    ts = record.get("timestamp", "")[11:19]  # HH:MM:SS
    content = record.get("content", "")
    meta = record.get("metadata", {})

    if t == "__session_start__":
        core.console.print(f"\n[bold]▶️ Сессия: {record.get('session_id')}[/bold]")
        core.console.print(f"   Агент: {record.get('agent_name')}")
        core.console.print(f"   Начало: {record.get('started_at')}")
    elif t == "__session_end__":
        core.console.print(f"[bold]⏹️ Завершено: {record.get('finished_at')}[/bold]")
        core.console.print(f"   Шагов: {record.get('steps_count')}")
    elif t == "llm_call":
        model = meta.get("model", "?")
        core.console.print(f"[dim]{ts}[/dim] [blue]🧠 LLM ({model})[/blue] {content[:200]}...")
    elif t == "tool_call":
        tool = meta.get("tool_name", "?")
        core.console.print(f"[dim]{ts}[/dim] [yellow]🔧 {tool}({content[:100]})[/yellow]")
    elif t == "tool_result":
        core.console.print(f"[dim]{ts}[/dim] [green]  → {content[:200]}...[/green]")
    elif t == "final":
        core.console.print(f"[dim]{ts}[/dim] [bold green]✅ Ответ: {content[:300]}...[/bold green]")
    elif t == "system":
        core.console.print(f"[dim]{ts}[/dim] [magenta]⚙️ {content[:200]}...[/magenta]")
    else:
        core.console.print(f"[dim]{ts}[/dim] {t}: {content[:200]}...")


def cmd_tools(args: argparse.Namespace):
    """Показать список зарегистрированных инструментов."""
    import core_tools  # регистрирует инструменты

    core.console.print("[bold cyan]🔧 Зарегистрированные инструменты:[/bold cyan]")
    tools_help = core._GLOBAL_REGISTRY.list_tools()
    if tools_help:
        core.console.print(tools_help)
    else:
        core.console.print("[yellow]Нет зарегистрированных инструментов.[/yellow]")


def cmd_mcp(args: argparse.Namespace):
    """Управление MCP-серверами."""
    from modules.mcp_client import MCPManager

    if args.action == "connect":
        core.console.print("[bold cyan]🔌 Подключение MCP-серверов...[/bold cyan]")
        manager = MCPManager()
        count = manager.connect_all()
        core.console.print(f"[green]✅ Подключено MCP-инструментов: {count}[/green]")
    elif args.action == "list":
        import json
        config_path = "mcp_servers.json"
        if not os.path.exists(config_path):
            core.console.print("[yellow]📭 Конфиг mcp_servers.json не найден.[/yellow]")
            return
        with open(config_path) as f:
            config = json.load(f)
        servers = config.get("servers", {})
        if not servers:
            core.console.print("[yellow]📭 Нет серверов в конфиге.[/yellow]")
            return
        core.console.print("[bold cyan]📋 MCP-серверы:[/bold cyan]")
        for name, cfg in servers.items():
            transport = cfg.get("transport", "?")
            desc = cfg.get("description", "")
            core.console.print(f"  [green]{name}[/green] ({transport}): {desc}")


def _load_session_history(app, session_id: str):
    """Загрузить историю чата из трейса сессии."""
    jsonl_path = os.path.join("traces", session_id, "trace.jsonl")
    if not os.path.exists(jsonl_path):
        core.console.print(f"[yellow]⚠️ Сессия {session_id} не найдена.[/yellow]")
        return

    with open(jsonl_path) as f:
        for line in f:
            record = json.loads(line)
            if record.get("type") == "llm_call":
                app.add_chat_message("ai", record.get("content", "")[:500])
            elif record.get("type") == "system":
                app.add_chat_message("system", record.get("content", "")[:500])


def main():
    parser = argparse.ArgumentParser(
        description="🤖 Autonomous AI Software Engineer — консольный инструмент",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  agent chat                     # TUI-чат с CasualAgent
  agent chat --model qwen3:8b    # с другой моделью
  agent chat --session session_20261027_120000  # возобновить сессию
  agent migrate                  # конвейер миграции
  agent trace list               # список сессий
  agent trace show 1             # просмотр первой сессии
  agent tools                    # список инструментов
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Подкоманда")

    # chat
    chat_parser = subparsers.add_parser("chat", help="TUI-чат с CasualAgent")
    chat_parser.add_argument("--model", "-m", default="", help="Модель для чата")
    chat_parser.add_argument("--session", "-s", default="", help="ID сессии для возобновления")

    # migrate
    migrate_parser = subparsers.add_parser("migrate", help="Конвейер миграции легаси-кода")

    # trace
    trace_parser = subparsers.add_parser("trace", help="Просмотр трейсов")
    trace_parser.add_argument("action", nargs="?", default="list",
                              choices=["list", "show"], help="Действие")
    trace_parser.add_argument("n", nargs="?", default=None, help="Номер сессии для show")

    # tools
    tools_parser = subparsers.add_parser("tools", help="Список инструментов")

    # mcp
    mcp_parser = subparsers.add_parser("mcp", help="Управление MCP-серверами")
    mcp_parser.add_argument("action", nargs="?", default="list",
                            choices=["connect", "list"],
                            help="Действие: connect (подключить) или list (список)")

    args = parser.parse_args()

    if args.command == "chat":
        cmd_chat(args)
    elif args.command == "migrate":
        cmd_migrate(args)
    elif args.command == "trace":
        cmd_trace(args)
    elif args.command == "tools":
        cmd_tools(args)
    elif args.command == "mcp":
        cmd_mcp(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
