# -*- coding: utf-8 -*-
# modules/permissions.py — Система разрешений (Фаза 2.3)

from typing import Optional


_PERMISSION_LEVELS = {
    "read": "free",       # чтение — свободно
    "write": "confirm",   # запись — с подтверждением
    "dangerous": "confirm",  # опасные операции — с подтверждением
}


def set_permission_level(category: str, level: str):
    """Изменить уровень разрешения для категории."""
    if category in _PERMISSION_LEVELS:
        _PERMISSION_LEVELS[category] = level


def get_permission_level(category: str) -> str:
    """Получить уровень разрешения для категории."""
    return _PERMISSION_LEVELS.get(category, "confirm")


def confirm_action(description: str, category: str = "write") -> bool:
    """Запросить подтверждение у пользователя.

    Возвращает True если разрешено, False если запрещено.
    """
    level = get_permission_level(category)

    if level == "free":
        return True

    if level == "deny":
        from rich.console import Console
        Console().print(f"[red]🚫 Заблокировано: {description}[/red]")
        return False

    # confirm — спрашиваем пользователя
    from rich.console import Console
    console = Console()

    console.print(f"\n[yellow]🔐 Разрешение: {description}[/yellow]")
    console.print("[dim]Разрешить? (y/n, всегда для сессии — Y/N)[/dim]")

    try:
        import curses
        stdscr = curses.initscr()
        curses.curs_set(1)
        stdscr.addstr(0, 0, f"Разрешить? (y/n, Y/N): ".ljust(80))
        stdscr.refresh()

        response = ""
        while True:
            key = stdscr.getch()
            if key in [ord('y'), ord('Y'), ord('n'), ord('N'), 10, 13, 27]:
                if key == 27:  # ESC
                    response = "n"
                    break
                elif key in [10, 13]:  # Enter
                    if response:
                        break
                else:
                    response = chr(key)
                    break
            elif key == curses.KEY_BACKSPACE or key == 127:
                response = ""
                stdscr.move(0, 0)
                stdscr.clrtoe()
                stdscr.addstr(0, 0, f"Разрешить? (y/n, Y/N): ".ljust(80))
                stdscr.refresh()

        curses.endwin()
    except Exception:
        # fallback на консольный ввод
        response = input("Разрешить? (y/n, Y/N): ").strip().lower()

    if response == 'Y':
        # Всегда для сессии
        set_permission_level(category, "free")
        console.print(f"[green]✅ {category}: разрешено на сессию[/green]")
        return True
    elif response == 'y':
        return True
    elif response == 'N':
        set_permission_level(category, "deny")
        console.print(f"[red]🚫 {category}: заблокировано на сессию[/red]")
        return False
    else:
        return False