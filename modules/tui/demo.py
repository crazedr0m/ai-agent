# -*- coding: utf-8 -*-
"""Demo script for TUI — shows UI without curses."""

from datetime import datetime

from core import runtime as _root_core

console = _root_core.console


def demo_simple():
    """Simple demo mode."""
    
    from modules.tui.app import TUIApp
    
    console.print("[bold green]DEMO MODE: Simple TUI[/bold green]")
    console.print("[dim](without curses, only rich)[/dim]\n")
    
    app = TUIApp(width=120, height=30)
    
    # Add test data
    app.add_chat_message("system", "AUTONOMOUS AI SOFTWARE ENGINEER started")
    app.add_chat_message("user", "Hello! How are you?")
    app.add_chat_message("ai", "Hello! I'm ready to help with legacy code migration.")
    
    # Add tasks
    app.update_task_status("task_1", "running", name="Migrating core.py", progress=25)
    app.update_task_status("task_2", "completed", name="Creating SDD")
    
    # Add files
    app.add_file("core.py")
    app.add_file("agents/migration_agent.py")
    app.add_file("modules/executor.py")
    app.add_file("shared_context.json")
    
    console.print("[bold cyan]UI:[/bold cyan]")
    console.print(app._build_ui())
    console.print("")


def demo_with_events():
    """Demo with event handlers."""
    
    from modules.tui.app import TUIApp
    
    console.print("[bold green]DEMO MODE: TUI with event handlers[/bold green]\n")
    
    app = TUIApp(width=120, height=30)
    
    # Mock event handlers
    def on_message(msg):
        console.print(f"[green]Event: {msg}[/green]")
    
    def on_task(task_id, status):
        console.print(f"[yellow]Task {task_id}: {status}[/yellow]")
    
    app.on_new_message = on_message
    app.on_task_complete = on_task
    
    # Add messages with event handlers
    app.add_chat_message("user", "Start migration!")
    app.add_chat_message("ai", "OK, starting project analysis...")
    
    console.print("[bold cyan]UI:[/bold cyan]")
    console.print(app._build_ui())
    console.print("")


def demo_live_update():
    """Demo live update (simulation)."""
    
    from modules.tui.app import TUIApp
    
    console.print("[bold green]DEMO MODE: Live Update[/bold green]\n")
    
    app = TUIApp(width=120, height=30)
    
    # Simulate task execution with progress
    task_id = "task_1"
    name = "Migrating core.py"
    
    for progress in [10, 25, 40, 60, 80, 95, 100]:
        app.update_task_status(task_id, "running", name=name, progress=progress)
        
        # Simulate delay
        import time
        time.sleep(0.5)
    
    console.print("[bold cyan]UI after completion:[/bold cyan]")
    console.print(app._build_ui())
    console.print("")


def demo_chat_export():
    """Demo chat export."""
    
    from modules.tui.app import TUIApp
    
    app = TUIApp(width=120, height=30)
    
    # Add messages
    app.add_chat_message("system", "AUTONOMOUS AI SOFTWARE ENGINEER started")
    app.add_chat_message("user", "Hello!")
    app.add_chat_message("ai", "Hello! I'm ready to help.")
    app.add_chat_message("user", "How does TUI work?")
    app.add_chat_message("ai", "TUI uses Rich for rendering and Curses for input.")
    
    console.print("[bold cyan]Chat export in Markdown:[/bold cyan]")
    
    lines = ["# Chat Export", ""]
    
    for role, content in app.chat_history:
        prefix = "**[User]**" if role == "user" else \
                "**[AI]**" if role == "ai" else f"**[{role.upper()}]**"
        lines.append(f"{prefix}\n{content}")
        lines.append("")
    
    console.print("\n".join(lines))


def demo_help():
    """Demo help."""
    
    from modules.tui.app import TUIApp
    
    app = TUIApp(width=120, height=30)
    
    console.print("[bold cyan]Hotkeys:[/bold cyan]")
    console.print("")
    console.print("  q — Exit")
    console.print("  n — New task")
    console.print("  c — Send message to chat")
    console.print("  t — Toggle tasks visibility")
    console.print("  f — Toggle files visibility")
    console.print("  u — Update status")
    console.print("  h — This help")
    console.print("")


def demo_full():
    """Full demo mode."""
    
    from modules.tui.app import TUIApp
    
    console.print("[bold green]DEMO MODE: Full[/bold green]\n")
    
    app = TUIApp(width=120, height=30)
    
    # Add messages
    app.add_chat_message("system", "AUTONOMOUS AI SOFTWARE ENGINEER started")
    app.add_chat_message("user", "Hello! How are you?")
    app.add_chat_message("ai", "Hello! I'm ready to help with legacy code migration.")
    
    # Add tasks
    app.update_task_status("task_1", "running", name="Migrating core.py", progress=25)
    app.update_task_status("task_2", "completed", name="Creating SDD")
    app.update_task_status("task_3", "pending", name="Writing tests")
    
    # Add files
    app.add_file("core.py")
    app.add_file("agents/migration_agent.py")
    app.add_file("modules/executor.py")
    app.add_file("shared_context.json")
    
    console.print("[bold cyan]UI:[/bold cyan]")
    console.print(app._build_ui())
    console.print("")


def main():
    """CLI interface for demo."""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Demo mode for TUI")
    parser.add_argument(
        "--mode", 
        choices=["simple", "events", "live", "chat", "help", "full"],
        default="full",
        help="Demo mode"
    )
    
    args = parser.parse_args()
    
    if args.mode == "simple":
        demo_simple()
    elif args.mode == "events":
        demo_with_events()
    elif args.mode == "live":
        demo_live_update()
    elif args.mode == "chat":
        demo_chat_export()
    elif args.mode == "help":
        demo_help()
    elif args.mode == "full":
        demo_full()


if __name__ == "__main__":
    main()
