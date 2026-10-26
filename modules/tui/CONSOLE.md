# 🖥️ Console Interface — Консольный интерфейс для TUI

## 📋 Overview

Документация консольного интерфейса **TUI** (Text User Interface) для взаимодействия с **MigrationAgent**.

---

## 🎯 Architecture

### Компоненты UI

```
┌─────────────────────────────────────────────────────┐
│  [Title Bar] 🤖 AUTONOMOUS AI SOFTWARE ENGINEER     │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────────┬────────────────────────────┐ │
│  │                  │                            │ │
│  │   CHAT PANEL     │    TASKS PANEL             │ │
│  │   (Сообщения)    │    (Список задач)          │ │
│  │                  │                            │ │
│  └──────────────────┴────────────────────────────┘ │
│                                                     │
│  ┌────────────────────────────────────────────────┐ │
│  │   FILES PANEL                                  │ │
│  │   (Файлы проекта, сгруппированные по папкам)   │ │
│  └────────────────────────────────────────────────┘ │
│                                                     │
├─────────────────────────────────────────────────────┤
│  STATUS BAR                                         │
│  Задачи: X в работе, Y завершено                    │
│  Чат: Z сообщений                                   │
│  [timestamp]: Сообщение                             │
└─────────────────────────────────────────────────────┘
```

---

## 🎨 Visual Elements

### Title Bar

**Формат:**
```
[bold blue]🤖 AUTONOMOUS AI SOFTWARE ENGINEER[/bold blue]
```

**Стиль:**
- Border: `blue`
- Box: `ROUNDED`

### Chat Panel

**Сообщения пользователя:**
```
[green][bold]>[/bold][/green] Пользователь
Сообщение пользователя
```

**Сообщения AI:**
```
[red][bold]<[/bold][/red] AI-Агент
Сообщение AI
```

**Системные сообщения:**
```
[dim]🤖 AUTONOMOUS AI SOFTWARE ENGINEER запущен[/dim]
```

### Tasks Panel

**Формат:**
```
task_1: ⏳ Миграция core.py
task_2: ✅ Создание SDD
task_3: ▶️ Написание тестов
```

**Статусы:**
- `⏳ pending` — ожидание (yellow)
- `▶️ running` — выполняется (green bold)
- `✅ completed` — завершено (green)
- `❌ failed` — ошибка (red)
- `🔄 retrying` — повторная попытка (orange)

### Files Panel

**Формат:**
```
core:
  • migration_agent.py
  • executor.py

agents:
  • retry_system.py
  • tracer.py
```

**Группировка по папкам с иконкой `📁`**

### Status Bar

**Счётчики:**
```
Задачи: 2 в работе, 1 завершено
Чат: 5 сообщений
```

**Последние статусы:**
```
15:30: Статус обновлён
15:31: Задача task_1 выполнена
15:32: Ошибка в задаче task_2
```

---

## 🎮 Hotkeys Reference

| Клавиша | Действие | Описание |
|---------|----------|----------|
| `q`     | quit     | Выход из приложения |
| `n`     | new_task | Создать новую задачу |
| `c`     | chat     | Отправить сообщение в чат |
| `t`     | toggle_tasks | Показать/скрыть задачи |
| `f`     | toggle_files  | Показать/скрыть файлы |
| `u`     | update   | Обновить статус |
| `h`     | help     | Отображение помощи |

---

## 📊 State Display

### Задачи (Tasks)

**Формат:**
```
task_1: ⏳ Миграция core.py
task_2: ✅ Создание SDD
task_3: ▶️ Написание тестов
task_4: ❌ Исправление ошибок
```

**Статусы:**
- `pending` — ожидание выполнения (⏳)
- `running` — выполняется сейчас (▶️)
- `completed` — успешно завершено (✅)
- `failed` — ошибка выполнения (❌)
- `retrying` — повторная попытка (🔄)

### Чат (Chat)

**Формат:**
```
[green][bold]>[/bold][/green] Пользователь
Привет! Как дела?

[red][bold]<[/bold][/red] AI-Агент
Привет! Я готов помочь с миграцией легаси-кода.
```

**Ограничение:** Отображаются последние 50 сообщений.

### Файлы (Files)

**Формат:**
```
core:
  • migration_agent.py
  • executor.py
  ... и ещё 2 файла

agents:
  • retry_system.py
  • tracer.py

modules:
  • parser.py
  • tracer.py
```

**Ограничение:** Отображаются первые 10 файлов на папку.

### Статус бар (Status Bar)

**Формат:**
```
Задачи: 2 в работе, 1 завершено
Чат: 5 сообщений
15:30: Статус обновлён
15:31: Задача task_1 выполнена
15:32: Ошибка в задаче task_2
```

**Ограничение:** Отображаются последние 3 статуса.

---

## 🔄 Live Updates

### Обновление частота

TUI обновляется **10 раз в секунду** (60 FPS не нужно для TUI).

```python
with Live(layout, console=self.console, refresh_per_second=10) as live:
    while True:
        # Обработка событий
        pass
```

### Триггеры обновления

- Изменение `chat_history` — обновление чата
- Изменение `tasks` — обновление списка задач
- Изменение `project_files` — обновление файлов
- Нажатие горячей клавиши — немедленное обновление

---

## 📝 Examples

### Пример 1: Простой TUI

```python
from modules.tui.app import TUIApp

app = TUIApp(width=120, height=30)

# Добавляем сообщения в чат
app.add_chat_message("system", "🤖 AUTONOMOUS AI SOFTWARE ENGINEER запущен")
app.add_chat_message("user", "Привет!")
app.add_chat_message("ai", "Привет! Я готов помочь.")

# Добавляем задачу
app.update_task_status("task_1", "running", name="Миграция core.py", progress=25)

# Запускаем TUI
app.run()
```

**Вывод:**
```
[bold blue]🤖 AUTONOMOUS AI SOFTWARE ENGINEER[/bold blue]
┌───────────────────────────────────────────────┐
│ [green][bold]>[/bold][/green] Пользователь              │
│ Привет!                                       │
│                                               │
│ [red][bold]<[/bold][/red] AI-Агент                  │
│ Привет! Я готов помочь.                      │
└───────────────────────────────────────────────┘

📋 ЗАДАЧИ
task_1: ▶️ Миграция core.py

📁 ФАЙЛЫ
core:
  • migration_agent.py
  • executor.py

Задачи: 1 в работе, 0 завершено
Чат: 3 сообщения
```

### Пример 2: Интеграция с MigrationAgent

```python
from agents.migration_agent import MigrationAgent
from modules.tui.app import TUIApp

# Создаём agent и TUI
agent = MigrationAgent()
app = TUIApp(width=120, height=30)

# Привязываем event handlers
app.on_new_message = lambda msg: console.print(f"[green]📨 {msg}[/green]")
app.on_task_complete = lambda tid, status: console.print(
    f"[yellow]📋 Задача {tid}: {status}[/yellow]"
)

# Можно также читать shared_context.json для обновления UI
if os.path.exists("shared_context.json"):
    import json
    with open("shared_context.json", "r") as f:
        ctx = json.load(f)
    
    for task_id, data in ctx.get("shared_state", {}).get(
        "sdd_documents", {}
    ).items():
        app.update_task_status(
            task_id,
            "completed" if data.get("iteration", 0) > 1 else "running",
            name=f"SDD для {task_id}",
            progress=100 if data.get("iteration", 0) > 1 else 50
        )

console.print("[bold green]TUI готов к работе с MigrationAgent![/bold green]")
app.run()
```

---

## 🎨 Styling

### Цветовая схема

| Элемент | Цвет | Стиль |
|---------|------|-------|
| Заголовок | blue | bold |
| Чат (пользователь) | green | bold prefix |
| Чат (AI) | red | bold prefix |
| Задачи (pending) | yellow | - |
| Задачи (running) | green | bold |
| Задачи (completed) | green | - |
| Задачи (failed) | red | - |
| Файлы | cyan | - |
| Статус бар | dim | - |

### Borders и Boxes

| Элемент | Border | Box |
|---------|--------|-----|
| Чат панель | default | SIMPLE |
| Задачи панель | yellow | SIMPLE |
| Файлы панель | cyan | SIMPLE |
| Заголовок | blue | ROUNDED |

---

## 📚 Related Documentation

- [README.md](../README.md) — основная документация TUI модуля
- [api.md](../api.md) — API reference
- [keys.md](../keys.md) — горячие клавиши
- [integration.md](../integration.md) — интеграция с MigrationAgent
- [examples_api.py](../examples_api.py) — примеры использования

---

## ✅ Summary

| Компонент | Описание |
|-----------|----------|
| Title Bar | Заголовок с названием приложения |
| Chat Panel | История сообщений чата (последние 50) |
| Tasks Panel | Список задач со статусами |
| Files Panel | Файлы проекта, сгруппированные по папкам |
| Status Bar | Счётчики и последние сообщения |
