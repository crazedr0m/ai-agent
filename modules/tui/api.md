# 📚 API Reference — TUI Module API Documentation

## 🎯 Overview

Этот документ описывает полный API **TUIApp** класса для интеграции с MigrationAgent.

---

## 🏗️ TUIApp Class

### Конструктор

#### `__init__(width: int = 120, height: int = 30)`

Инициализирует TUI приложение.

**Параметры:**
- `width` (int, default=120) — ширина терминала в символах
- `height` (int, default=30) — высота терминала в строках

**Пример:**
```python
app = TUIApp(width=120, height=30)
```

---

## 📊 State Properties

### `chat_history: list[tuple[str, str]]`

История сообщений чата.

**Формат:**
```python
[
    ("user", "Привет!"),
    ("ai", "Привет! Как дела?"),
    ("system", "🤖 AUTONOMOUS AI SOFTWARE ENGINEER запущен")
]
```

### `tasks: dict[str, dict]`

Словарь задач со статусами.

**Формат:**
```python
{
    "task_1": {
        "id": "task_1",
        "name": "Миграция core.py",
        "status": "running",  # pending, running, completed, failed, retrying
        "progress": 25.0
    }
}
```

### `project_files: list[dict]`

Список файлов проекта.

**Формат:**
```python
[
    {
        "path": "core.py",
        "timestamp": "2026-10-12T15:30:00"
    }
]
```

### `status_messages: list[tuple[str, str]]`

Список статусов (timestamp, message).

**Формат:**
```python
[
    ("15:30", "Статус обновлён"),
    ("15:31", "Задача task_1 выполнена")
]
```

### `show_tasks: bool`

Флаг видимости панели задач.

**Пример:**
```python
app.show_tasks = False  # Скрыть задачи
```

### `show_files: bool`

Флаг видимости панели файлов.

**Пример:**
```python
app.show_files = False  # Скрыть файлы
```

---

## 🎮 Event Handlers

### `on_new_message: Optional[Callable]`

Обработчик новых сообщений чата.

**Тип:**
```python
Optional[Callable[[str, str], None]]
```

**Параметры:**
- `role` (str) — роль: "user", "ai", "system"
- `content` (str) — содержимое сообщения

**Пример:**
```python
app.on_new_message = lambda role, content: console.print(
    f"[green]📨 [{role}] {content}[/green]"
)
```

### `on_task_complete: Optional[Callable]`

Обработчик завершения задач.

**Тип:**
```python
Optional[Callable[[str, str, str, float], None]]
```

**Параметры:**
- `task_id` (str) — ID задачи
- `status` (str) — новый статус: "pending", "running", "completed", "failed"
- `name` (str, optional) — имя задачи
- `progress` (float, optional) — прогресс от 0 до 100

**Пример:**
```python
app.on_task_complete = lambda tid, status, name=None, progress=0: console.print(
    f"[yellow]📋 {tid}: {status} — {name or ''} ({progress:.0f}%)[/yellow]"
)
```

---

## 🚀 Public Methods

### `run()`

Запускает event loop приложения.

**Описание:**
Запускает curses-based event loop с обработкой горячих клавиш.

**Пример:**
```python
app.run()
```

**Горячие клавиши:**
- `q` — выход из приложения
- `n` — новая задача
- `c` — отправить сообщение в чат
- `t` — показать/скрыть задачи
- `f` — показать/скрыть файлы
- `u` — обновить статус
- `h` — помощь

---

### `add_chat_message(role: str, content: str)`

Добавляет сообщение в чат.

**Параметры:**
- `role` (str) — роль отправителя: "user", "ai", "system"
- `content` (str) — содержимое сообщения

**Пример:**
```python
app.add_chat_message("user", "Привет!")
app.add_chat_message("ai", "Привет! Как дела?")
```

---

### `update_task_status(task_id: str, status: str, name: str = None, progress: float = 0)`

Обновляет статус задачи.

**Параметры:**
- `task_id` (str) — ID задачи (например, "task_1")
- `status` (str) — статус:
  - `"pending"` — ожидание
  - `"running"` — выполняется
  - `"completed"` — завершено
  - `"failed"` — ошибка
  - `"retrying"` — повторная попытка
- `name` (str, optional) — имя задачи
- `progress` (float, optional) — прогресс от 0 до 100

**Пример:**
```python
app.update_task_status("task_1", "running", name="Миграция core.py", progress=25)
```

---

### `add_file(path: str)`

Добавляет файл проекта.

**Параметры:**
- `path` (str) — путь к файлу

**Пример:**
```python
app.add_file("core.py")
app.add_file("agents/migration_agent.py")
app.add_file("modules/executor.py")
```

---

### `_on_quit()`

Обработчик выхода из приложения.

**Описание:**
Вызывается при нажатии `q`. Выводит сообщение и завершает программу.

---

### `_on_new_task()`

Создаёт новую задачу.

**Описание:**
Вызывается при нажатии `n`. Создаёт задачу со статусом "pending".

**Пример:**
```python
app._on_new_task()  # Создать новую задачу
```

---

### `_on_chat()`

Обработчик отправки сообщения в чат.

**Описание:**
Вызывается при нажатии `c`. Читает ввод пользователя и добавляет в chat_history.

**Пример:**
```python
app._on_chat()  # Открыть ввод сообщения
```

---

### `_on_toggle_tasks()`

Переключает видимость панели задач.

**Описание:**
Вызывается при нажатии `t`. Инвертирует флаг `show_tasks`.

**Пример:**
```python
app._on_toggle_tasks()  # Показать/скрыть задачи
```

---

### `_on_toggle_files()`

Переключает видимость панели файлов.

**Описание:**
Вызывается при нажатии `f`. Инвертирует флаг `show_files`.

**Пример:**
```python
app._on_toggle_files()  # Показать/скрыть файлы
```

---

### `_on_update()`

Обновляет статус приложения.

**Описание:**
Вызывается при нажатии `u`. Добавляет сообщение в status_messages.

**Пример:**
```python
app._on_update()  # Обновить статус
```

---

### `_on_help()`

Отображает помощь.

**Описание:**
Вызывается при нажатии `h`. Выводит список горячих клавиш.

**Пример:**
```python
app._on_help()  # Показать помощь
```

---

## 🎨 Rendering Methods

### `_build_ui()`

Собирает UI компоненты в строку.

**Возвращает:**
`str` — отформатированный UI с чатом, задачами, файлами и статусом.

**Пример:**
```python
ui_string = app._build_ui()
console.print(ui_string)
```

---

### `_render_chat()`

Рендерит панель чата.

**Возвращает:**
`str` — отформатированный текст чата.

**Формат:**
```
[green][bold]>[/bold][/green] Пользователь
Сообщение пользователя

[red][bold]<[/bold][/red] AI-Агент
Сообщение AI
```

---

### `_render_tasks()`

Рендерит панель задач.

**Возвращает:**
`str` — отформатированный текст списка задач.

**Формат:**
```
task_1: ⏳ Миграция core.py
task_2: ✅ Создание SDD
task_3: ▶️ Написание тестов
```

---

### `_render_files()`

Рендерит панель файлов.

**Возвращает:**
`str` — отформатированный текст списка файлов, сгруппированных по папкам.

**Формат:**
```
core:
  • migration_agent.py
  • executor.py

agents:
  • retry_system.py
```

---

### `_render_status()`

Рендерит статус бар.

**Возвращает:**
`str` — отформатированный текст со счётчиками и последними сообщениями.

**Формат:**
```
Задачи: 2 в работе, 1 завершено
Чат: 5 сообщений
15:30: Статус обновлён
```

---

### `_render()`

Рендерит полный UI с заголовком.

**Возвращает:**
`Panel` — Rich Panel с заголовком и содержимым.

**Пример:**
```python
panel = app._render()
console.print(panel)
```

---

### `_init_layout()`

Инициализирует layout.

**Описание:**
Создаёт Layout структуру для split панелей (chat, tasks, files, status).

---

## 🔌 Integration Methods

### `emit_chat_message(role: str, content: str)`

Эмитит сообщение в чат (для MigrationAgent).

**Параметры:**
- `role` (str) — роль отправителя
- `content` (str) — содержимое сообщения

**Пример:**
```python
agent.emit_chat_message("user", "Привет!")
```

---

### `emit_task_status(task_id: str, status: str, name: str = None, progress: float = 0)`

Эмитит изменение статуса задачи (для MigrationAgent).

**Параметры:**
- `task_id` (str) — ID задачи
- `status` (str) — новый статус
- `name` (str, optional) — имя задачи
- `progress` (float, optional) — прогресс

**Пример:**
```python
agent.emit_task_status("task_1", "running", name="Миграция core.py", progress=25)
```

---

### `emit_file_discovered(path: str)`

Эмитит обнаружение файла (для MigrationAgent).

**Параметры:**
- `path` (str) — путь к файлу

**Пример:**
```python
agent.emit_file_discovered("core.py")
```

---

## 📊 Status Icons

### Задачи

| Статус | Иконка | Цвет |
|--------|--------|------|
| pending | `⏳` | yellow |
| running | `▶️` | green (bold) |
| completed | `✅` | green |
| failed | `❌` | red |
| retrying | `🔄` | orange |

### Роль сообщений

| Роль | Префикс | Цвет |
|------|---------|------|
| user | `[green]>[/green]` | green |
| ai | `[red]<[/red]` | red |
| system | `[dim]` | gray |

---

## 🧪 Examples

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

### Пример 2: Интеграция с MigrationAgent

```python
from agents.migration_agent import MigrationAgent
from modules.tui.app import TUIApp

class IntegratedMigrationAgent(MigrationAgent):
    """MigrationAgent с event emission."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tui_app = None
    
    def set_tui(self, app):
        """Устанавливает TUIApp для event emission."""
        self._tui_app = app
        
        # Привязываем event handlers
        self.on_chat_message = lambda role, content: \
            self._tui_app.add_chat_message(role, content) if self._tui_app else None
        
        self.on_task_status_change = lambda tid, status, name=None, progress=0: \
            self._tui_app.update_task_status(tid, status, name, progress) \
            if self._tui_app else None

# Создаём integrated agent
agent = IntegratedMigrationAgent()

# Создаём TUI и привязываем event handlers
app = TUIApp(width=120, height=30)
agent.set_tui(app)

# Запускаем agent (он будет эмитить события в TUI)
agent.run()
```

### Пример 3: Использование через shared_context.json

```python
from modules.tui.app import TUIApp

app = TUIApp(width=120, height=30)

# Загружаем shared_context.json для обновления UI
if os.path.exists("shared_context.json"):
    with open("shared_context.json", "r") as f:
        ctx = json.load(f)
    
    # Восстанавливаем задачи из shared context
    for task_id, data in ctx.get("shared_state", {}).get(
        "sdd_documents", {}
    ).items():
        app.update_task_status(
            task_id,
            "completed" if data.get("iteration", 0) > 1 else "running",
            name=f"SDD для {task_id}",
            progress=100 if data.get("iteration", 0) > 1 else 50
        )

app.run()
```

---

## 📦 Dependencies

- `rich` — уже в requirements.txt
- `curses` — стандартная библиотека Python на Linux/Mac

**Дополнительные зависимости (не обязательны):**
- (нет)

---

## 🔧 Advanced Usage

### Live Update Loop

TUI использует `Live()` контекстный менеджер от Rich для live updates:

```python
from rich.live import Live

with Live(layout, console=self.console, refresh_per_second=10) as live:
    while True:
        key = stdscr.getch()  # Чтение клавиши
        
        if key == -1 or key == ord('q'):
            break
        
        action, description = self.HOTKEYS.get(key.lower())
        
        if action:
            core_func = getattr(self, f"_on_{action}", None)
            if core_func:
                core_func()
```

**refresh_per_second=10** — обновление UI 10 раз в секунду (60 FPS не нужно для TUI).

---

## 📝 Notes

- **IMMUTABLE files:** `_core.py`, `core.py`, `core_tools.py` cannot be modified
- **Shared context pattern:** Используется для передачи данных между этапами конвейера (SDD→TDD→Coding)
- **Parallel execution:** asyncio.gather() используется для параллельного выполнения задач

---

## ✅ Summary

| Method | Description |
|--------|-------------|
| `__init__(width, height)` | Инициализация TUI приложения |
| `run()` | Запуск event loop |
| `add_chat_message(role, content)` | Добавление сообщения в чат |
| `update_task_status(task_id, status, name=None, progress=0)` | Обновление статуса задачи |
| `add_file(path)` | Добавление файла проекта |
| `_on_quit()` | Обработчик выхода (q) |
| `_on_new_task()` | Создание новой задачи (n) |
| `_on_chat()` | Отправка сообщения в чат (c) |
| `_on_toggle_tasks()` | Переключение видимости задач (t) |
| `_on_toggle_files()` | Переключение видимости файлов (f) |
| `_on_update()` | Обновление статуса (u) |
| `_on_help()` | Отображение помощи (h) |

---

## 📚 Related Documentation

- [README.md](../README.md) — основная документация TUI модуля
- [integration.md](../integration.md) — интеграция с MigrationAgent
- [examples_api.py](../examples_api.py) — примеры использования
- [demo.py](../demo.py) — демо режим
