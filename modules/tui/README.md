# 🤖 TUI Module — Text User Interface для Autonomous AI Software Engineer

## 📋 Описание

TUI (Text User Interface) модуль предоставляет консольный интерфейс для взаимодействия с **MigrationAgent** в реальном времени. 

Интерфейс отображает:
- 💬 **Чат** — история сообщений между пользователем и AI-агентом
- 📋 **Задачи** — список задач со статусами (pending/running/completed/failed)
- 📁 **Файлы** — файловый эксплорер проекта с группировкой по папкам
- 📊 **Статус** — счётчики и последние сообщения

## ✨ Особенности

- ✅ **Rich-based rendering** — использует библиотеку Rich для красивого отображения
- ✅ **Curses input handling** — поддержка клавиатуры через curses
- ✅ **Live updates** — обновление UI в реальном времени (10 FPS)
- ✅ **Component architecture** — модульная структура компонентов
- ✅ **Event-driven** — event handlers для интеграции с MigrationAgent
- ✅ **Hotkeys** — горячие клавиши для навигации

## 📁 Структура

```
modules/tui/
├── __init__.py          # Экспорт модуля
├── app.py               # Main TUIApp class (434 lines)
├── components.py        # UI компоненты (ChatPanel, TaskList, StatusBar, FileExplorer)
├── demo.py              # Demo скрипт без curses
├── examples_api.py      # Примеры использования API
├── README.md            # Эта документация
├── api.md               # API reference
├── keys.md              # Горячие клавиши
├── CONSOLE.md           # Console interface docs
└── integration.md       # Integration guide (draft)
```

## 🚀 Быстрый старт

### 1. Простой TUI без интеграции

```python
from modules.tui.app import TUIApp

app = TUIApp(width=120, height=30)

# Добавляем сообщения в чат
app.add_chat_message("system", "🤖 AUTONOMOUS AI SOFTWARE ENGINEER запущен")
app.add_chat_message("user", "Привет!")
app.add_chat_message("ai", "Привет! Я готов помочь.")

# Добавляем задачу
app.update_task_status("task_1", "running", name="Миграция core.py", progress=25)

app.run()
```

### 2. Запуск через demo.py

```bash
# Простой демо режим
python modules/tui/demo.py --mode simple

# Полный демо режим
python modules/tui/demo.py --mode full

# Экспорт чата в Markdown
python modules/tui/demo.py --mode chat
```

### 3. Интеграция с MigrationAgent

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
    with open("shared_context.json", "r", encoding="utf-8") as f:
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

app.run()
```

## 🎮 Горячие клавиши

| Клавиша | Действие | Описание |
|---------|----------|----------|
| `q`     | quit     | Выход из приложения |
| `n`     | new_task | Создать новую задачу |
| `c`     | chat     | Отправить сообщение в чат |
| `t`     | toggle_tasks | Показать/скрыть задачи |
| `f`     | toggle_files  | Показать/скрыть файлы |
| `u`     | update   | Обновить статус |
| `h`     | help     | Отображение помощи |

## 📊 API Reference

### TUIApp.__init__(width, height)

Конструктор класса.

**Параметры:**
- `width` (int, default=120) — ширина терминала
- `height` (int, default=30) — высота терминала

### TUIApp.add_chat_message(role, content)

Добавить сообщение в чат.

**Параметры:**
- `role` (str) — роль отправителя: "user", "ai", "system"
- `content` (str) — содержимое сообщения

**Пример:**
```python
app.add_chat_message("user", "Привет!")
app.add_chat_message("ai", "Привет! Как дела?")
```

### TUIApp.update_task_status(task_id, status, name=None, progress=0)

Обновить статус задачи.

**Параметры:**
- `task_id` (str) — ID задачи (например, "task_1")
- `status` (str) — статус: "pending", "running", "completed", "failed"
- `name` (str, optional) — имя задачи
- `progress` (float, optional) — прогресс от 0 до 100

**Пример:**
```python
app.update_task_status("task_1", "running", name="Миграция core.py", progress=25)
```

### TUIApp.add_file(path)

Добавить файл проекта.

**Параметры:**
- `path` (str) — путь к файлу

**Пример:**
```python
app.add_file("core.py")
app.add_file("agents/migration_agent.py")
```

### TUIApp.on_new_message(callback)

Установить обработчик новых сообщений чата.

**Параметры:**
- `callback` (Callable) — функция вызываемая при новом сообщении

**Пример:**
```python
app.on_new_message = lambda msg: console.print(f"[green]📨 {msg}[/green]")
```

### TUIApp.on_task_complete(callback)

Установить обработчик завершения задач.

**Параметры:**
- `callback` (Callable) — функция вызываемая при изменении статуса задачи

**Пример:**
```python
app.on_task_complete = lambda tid, status: console.print(f"[yellow]📋 {tid}: {status}[/yellow]")
```

## 🔄 Live Update Loop

TUI использует `Live()` контекстный менеджер от Rich для live updates:

```python
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

## 📦 Зависимости

TUI использует только существующие зависимости проекта:

- `rich` — уже в requirements.txt
- `curses` — стандартная библиотека Python на Linux/Mac

**Дополнительные зависимости (не обязательны):**
- (нет)

## 🧪 Тестирование

### Запуск демо режима

```bash
# Простой демо режим
python modules/tui/demo.py --mode simple

# Полный демо режим
python modules/tui/demo.py --mode full

# Экспорт чата в Markdown
python modules/tui/demo.py --mode chat

# Горячие клавиши
python modules/tui/demo.py --mode help
```

### Запуск через examples_api.py

```bash
# Простой TUI
python modules/tui/examples_api.py --mode simple

# Демо режим
python modules/tui/examples_api.py --mode demo

# Интеграция с MigrationAgent
python modules/tui/examples_api.py --mode integration
```

## 📝 Примеры использования

См. `examples_api.py` для полных примеров:

- **Пример 1:** Простой TUI без интеграции
- **Пример 2:** Интеграция с MigrationAgent
- **Пример 3:** Полная интеграция с MigrationAgent
- **Пример 4:** Загрузка задач из tasks.json
- **Пример 5:** Добавление файлов проекта
- **Пример 6:** Demo режим (без curses, только rich)
- **Пример 7:** Использование с asyncio
- **Пример 8:** Hot reload при изменении shared_context.json
- **Пример 9:** Мульти-оконный режим (требует модификации curses)
- **Пример 10:** Экспорт чата в Markdown

## 🔌 Интеграция с MigrationAgent

### Архитектура

```
┌─────────────────┐      ┌─────────────────┐
│   MigrationAgent │────>│     TUIApp      │
│                  │     │                 │
│ - on_chat_msg()  │<----│ - chat_history  │
│ - on_task_status()│    │ - tasks         │
│ - on_file_discovered()│    │ - project_files│
└─────────────────┘     └─────────────────┘
```

### Event Flow

1. **MigrationAgent** выполняет задачу: SDD → TDD → Coding → Tests → Critic
2. При каждом событии вызывает event handlers:
   ```python
   agent.on_chat_message(role, content)  # Добавляет в chat_history
   agent.on_task_status_change(task_id, status)  # Обновляет tasks dict
   agent.on_file_discovered(path)  # Добавляет в project_files
   ```
3. **TUIApp** обновляется через `Live()` loop и отображает изменения

### Shared Context Pattern

TUI может читать `shared_context.json` для получения данных:

```python
with open("shared_context.json", "r") as f:
    ctx = json.load(f)

for task_id, data in ctx.get("shared_state", {}).get(
    "sdd_documents", {}
).items():
    app.update_task_status(task_id, "completed" if data.get("iteration", 0) > 1 else "running")
```

## 🎨 UI Components

### ChatPanel

Отображает историю сообщений чата.

**Роль:**
- `[green]>[/green]` — пользователь
- `[red]<[/red]` — AI-агент

### TaskList

Отображает список задач со статусами:

- `⏳ pending` — ожидание
- `▶️ running` — выполняется
- `✅ completed` — завершено
- `❌ failed` — ошибка
- `🔄 retrying` — повторная попытка

### StatusBar

Отображает счётчики и последние сообщения:

- Задачи в работе / завершено
- Количество сообщений в чате
- Последние статусы (timestamp + message)

### FileExplorer

Группирует файлы по папкам с иконками.

## 🔒 Безопасность

TUI не выполняет код из чата — только отображает сообщения.

**Заблокировано:**
- Изменение `_core.py`, `core.py`, `core_tools.py` (IMMUTABLE)
- Выполнение произвольного кода из сообщений

**Разрешено:**
- Отображение сообщений в чате
- Чтение файлов проекта
- Обновление статусов задач

## 🚀 Next Steps

1. **Full MigrationAgent integration** — добавить методы `emit_chat_message()`, `emit_task_status()` в MigrationAgent
2. **Event loop implementation** — заменить `_read_key()` на curses input
3. **Live rendering with Live()** — реализовать proper refresh loop с 10 FPS
4. **Export functionality** — экспорт чата в Markdown/PDF
5. **Multi-window support** — несколько TUI инстансов для разных проектов

## 📚 Ссылки

- [API Reference](api.md) — полная документация API
- [Console Interface](CONSOLE.md) — описание console interface
- [Integration Guide](integration.md) — интеграция с MigrationAgent (draft)
- [Examples](examples_api.py) — примеры использования
- [Demo](demo.py) — демо режим

## ✅ User-Approved Items

- ✅ Use Rich library (already in requirements.txt)
- ✅ No dev dependencies (pytest, flake8, mypy forbidden)
- ✅ Shared context between pipeline stages (SDD→TDD→Coding)
- ✅ Parallel execution via asyncio.gather()
- ✅ Retry system with escalation

## 📄 License

Part of the Autonomous AI Software Engineer project.
