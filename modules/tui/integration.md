# 🔌 Integration Guide — Интеграция TUI с MigrationAgent

## 📋 Overview

Этот документ описывает полную интеграцию **TUI** (Text User Interface) с **MigrationAgent**.

### Архитектура

```
┌─────────────────────────────────────────────────────┐
│                    MigrationAgent                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │   SDD    │→ │   TDD    │→ │  Coding  │ ...       │
│  └──────────┘  └──────────┘  └──────────┘           │
│              ┌───────────────────────────┐          │
│              │     shared_context.json    │          │
│              └───────────────────────────┘          │
└──────────────┼────────────────────────────┬─────────┘
               │                            │
               ▼                            ▼
┌─────────────────────────────────────────────────────┐
│                      TUIApp                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │   Chat   │→ │  Tasks   │←┤  Status   │          │
│  └──────────┘  └──────────┘  └──────────┘          │
│              ┌───────────────────────────┐          │
│              │     project_files         │          │
│              └───────────────────────────┘          │
└─────────────────────────────────────────────────────┘
```

### Event Flow

1. **MigrationAgent** выполняет задачи: SDD → TDD → Coding → Tests → Critic
2. При каждом событии вызывает event handlers в **TUIApp**:
   - `on_chat_message()` — добавляет сообщение в чат
   - `on_task_status_change()` — обновляет статус задачи
   - `on_file_discovered()` — добавляет файл проекта

3. **TUIApp** обновляется через `Live()` loop и отображает изменения

## 🚀 Quick Start

### 1. Простая интеграция (через shared_context.json)

```python
from agents.migration_agent import MigrationAgent
from modules.tui.app import TUIApp

# Создаём agent и TUI
agent = MigrationAgent()
app = TUIApp(width=120, height=30)

# Загружаем shared_context.json для обновления UI
if os.path.exists("shared_context.json"):
    import json
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

# Запускаем TUI
app.run()
```

### 2. Полная интеграция (с event handlers)

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
    
    def emit_chat_message(self, role: str, content: str):
        """Эмитит сообщение в чат."""
        if self._tui_app and self._tui_app.on_new_message:
            self._tui_app.on_new_message(role, content)
    
    def emit_task_status(self, task_id: str, status: str, name=None, progress=0):
        """Эмитит изменение статуса задачи."""
        if self._tui_app and self._tui_app.on_task_complete:
            self._tui_app.on_task_complete(task_id, status, name, progress)

# Создаём integrated agent
agent = IntegratedMigrationAgent()

# Создаём TUI и привязываем event handlers
app = TUIApp(width=120, height=30)
agent.set_tui(app)

# Запускаем agent (он будет эмитить события в TUI)
agent.run()
```

## 📝 API Reference

### MigrationAgent.emit_chat_message(role, content)

Эмитит сообщение в чат.

**Параметры:**
- `role` (str) — роль: "user", "ai", "system"
- `content` (str) — содержимое сообщения

**Пример:**
```python
agent.emit_chat_message("user", "Привет!")
agent.emit_chat_message("ai", "Привет! Как дела?")
```

### MigrationAgent.emit_task_status(task_id, status, name=None, progress=0)

Эмитит изменение статуса задачи.

**Параметры:**
- `task_id` (str) — ID задачи
- `status` (str) — статус: "pending", "running", "completed", "failed"
- `name` (str, optional) — имя задачи
- `progress` (float, optional) — прогресс от 0 до 100

**Пример:**
```python
agent.emit_task_status("task_1", "running", name="Миграция core.py", progress=25)
```

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
- `task_id` (str) — ID задачи
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

## 🔌 Event Handlers

### on_new_message(callback)

Установить обработчик новых сообщений чата.

**Параметры:**
- `callback` (Callable[[str, str], None]) — функция вызываемая при новом сообщении

**Пример:**
```python
app.on_new_message = lambda role, content: console.print(
    f"[green]📨 [{role}] {content}[/green]"
)
```

### on_task_complete(callback)

Установить обработчик завершения задач.

**Параметры:**
- `callback` (Callable[[str, str, str, float], None]) — функция вызываемая при изменении статуса задачи

**Пример:**
```python
app.on_task_complete = lambda tid, status, name=None, progress=0: console.print(
    f"[yellow]📋 {tid}: {status} — {name or ''} ({progress:.0f}%)[/yellow]"
)
```

## 🔄 Shared Context Pattern

TUI может читать `shared_context.json` для получения данных о задачах:

```python
import json

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

# Также можно читать test_code и implementation_code
for task_id, data in ctx.get("shared_state", {}).get(
    "test_code", {}
).items():
    print(f"Test code for {task_id}: {data['file']}")

for task_id, data in ctx.get("shared_state", {}).get(
    "implementation_code", {}
).items():
    print(f"Implementation for {task_id}: {data['file']}")
```

## 📊 Status Updates

### Обновление статуса задачи в реальном времени

```python
# Имитация выполнения задачи с прогрессом
for progress in [10, 25, 40, 60, 80, 95, 100]:
    app.update_task_status("task_1", "running", name="Миграция core.py", progress=progress)
    
    # Имитация задержки (можно заменить на реальную работу)
    import time
    time.sleep(0.5)

# Завершение задачи
app.update_task_status("task_1", "completed", name="Миграция core.py", progress=100)
```

### Обновление статуса при ошибках

```python
# Ошибка в задаче
app.update_task_status("task_1", "failed", name="Миграция core.py", progress=80)

# Повторная попытка
app.update_task_status("task_1", "retrying", name="Миграция core.py", progress=0)
```

## 📁 File Explorer Updates

### Добавление файлов при выполнении задач

```python
# При создании SDD документа
app.add_file(f"sdd_{os.path.basename(target_file)}.md")

# При создании тестов
test_file = f"test_{os.path.basename(target_file)}"
app.add_file(test_file)

# При создании реализации
app.add_file(target_file)
```

### Группировка файлов по папкам

Файлы автоматически группируются по папкам:

```python
# Пример вывода в UI:
# 📁 ФАЙЛЫ
# 
# core:
#   • migration_agent.py
#   • executor.py
# agents:
#   • retry_system.py
# modules:
#   • parser.py
#   • tracer.py
```

## 🎯 Best Practices

### 1. Используйте shared_context.json для синхронизации

```python
def sync_tui_with_shared_context(app):
    """Синхронизирует TUI с shared_context.json."""
    if os.path.exists("shared_context.json"):
        with open("shared_context.json", "r") as f:
            ctx = json.load(f)
        
        # Обновляем задачи из SDD documents
        for task_id, data in ctx.get("shared_state", {}).get(
            "sdd_documents", {}
        ).items():
            app.update_task_status(
                task_id,
                "completed" if data.get("iteration", 0) > 1 else "running",
                name=f"SDD для {task_id}",
                progress=100 if data.get("iteration", 0) > 1 else 50
            )

# Вызовите эту функцию после запуска MigrationAgent
sync_tui_with_shared_context(app)
```

### 2. Используйте event handlers для live updates

```python
class LiveMigrationAgent(MigrationAgent):
    """MigrationAgent с live updates в TUI."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tui_app = None
    
    def set_tui(self, app):
        """Устанавливает TUIApp для event emission."""
        self._tui_app = app
        
        # Привязываем event handlers
        self.on_chat_message = lambda role, content: app.add_chat_message(role, content)
        self.on_task_status_change = lambda tid, status, name=None, progress=0: \
            app.update_task_status(tid, status, name, progress)

# Создаём live agent
agent = LiveMigrationAgent()

# Создаём TUI
app = TUIApp(width=120, height=30)

# Устанавливаем связь
agent.set_tui(app)

# Запускаем
agent.run()
```

### 3. Используйте hot reload для обновления промптов

```python
def sync_with_hot_reload(app):
    """Синхронизирует TUI с hot reload событий."""
    if os.path.exists("shared_context.json"):
        with open("shared_context.json", "r") as f:
            ctx = json.load(f)
        
        # Проверяем, был ли hot reload
        iteration_count = ctx.get("shared_state", {}).get(
            "iteration_count", 0
        )
        
        if iteration_count > 0:
            console.print(f"[yellow]🔄 Hot reload: {iteration_count} итераций[/yellow]")

# Вызовите эту функцию после core.hot_reload()
sync_with_hot_reload(app)
```

## 🧪 Testing

### Запуск TUI с демо данными

```bash
python modules/tui/demo.py --mode full
```

### Запуск через examples_api.py

```bash
python modules/tui/examples_api.py --mode integration
```

### Интеграция с реальным MigrationAgent

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

## 📚 Related Documentation

- [README.md](README.md) — основная документация TUI модуля
- [api.md](api.md) — API reference
- [keys.md](keys.md) — горячие клавиши
- [CONSOLE.md](CONSOLE.md) — console interface docs
- [examples_api.py](examples_api.py) — примеры использования

## ✅ Checklist

- [x] TUIApp class с event loop
- [x] UI компоненты (ChatPanel, TaskList, StatusBar, FileExplorer)
- [x] Demo режим без curses
- [x] Integration guide (этот документ)
- [ ] Full MigrationAgent integration (emit methods)
- [ ] Event loop implementation (curses input)
- [ ] Live rendering with Live()
- [ ] Export functionality (Markdown/PDF)

## 🔮 Next Steps

1. **Add emit methods to MigrationAgent** — добавить `emit_chat_message()` и `emit_task_status()` в MigrationAgent
2. **Implement proper keyboard input** — заменить `_read_key()` на curses input
3. **Create full integration example** — показать как запустить оба вместе
4. **Add live rendering loop** — реализовать proper refresh loop с 10 FPS
5. **Export functionality** — добавить экспорт чата в Markdown/PDF
