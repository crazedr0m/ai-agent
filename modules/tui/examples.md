# Примеры использования TUI

## 🎬 Сценарий 1: Мониторинг миграции в реальном времени

```bash
python -m modules.tui.example
```

**Что вы увидите:**
- Чат с историей диалогов между пользователем и AI-агентом
- Список задач с индикаторами статуса (⏳/▶️/✅/❌)
- Файловый эксплорер проекта
- Статус бар со счётчиками

**Интерактивность:**
- Нажмите `c` — отправьте сообщение в чат
- Нажмите `n` — создайте новую задачу
- Нажмите `u` — обновите статус выполнения

---

## 🎬 Сценарий 2: Отладка с выводом логов

```python
from modules.tui.app import TUIApp
from agents.migration_agent import MigrationAgent

# Создаём агента и TUI
agent = MigrationAgent()
app = TUIApp(width=100, height=30)

# Интегрируем события
def on_message(msg):
    print(f"[green]📩 Новое сообщение:[/green] {msg}")
    
def on_task_complete(task_id):
    print(f"[green]✅ Задача завершена:[/green] {task_id}")
    
app.on_new_message = on_message
app.on_task_complete = on_task_complete

# Запускаем
agent.run()
```

---

## 🎬 Сценарий 3: Статический просмотр истории

```python
from modules.tui.app import TUIApp

# Загружаем историю из shared_context.json
with open("shared_context.json") as f:
    context = json.load(f)
    
app = TUIApp()
app.chat_history = context.get("chat", [])
app.tasks = context.get("tasks", {})
app.project_files = context.get("files", [])

# Рендерим один раз (без event loop)
print(app._render())
```

---

## 🎬 Сценарий 4: Интеграция с asyncio

```python
import asyncio
from modules.tui.app import TUIApp

async def migration_loop():
    """Асинхронный цикл миграции."""
    
    while True:
        # Выполняем шаг миграции
        await agent.execute_step()
        
        # Обновляем state
        app.tasks = get_current_tasks()
        app.chat_history = get_chat_history()
        
        # Рендерим UI
        print(app._render())
        
        # Ждём 1 секунду
        await asyncio.sleep(1)

# Запускаем
asyncio.run(migration_loop())
```

---

## 🎬 Сценарий 5: Кастомизация компонентов

```python
from modules.tui.components import ChatPanel, TaskList

# Создаём кастомные компоненты
chat = ChatPanel(
    history=[("user", "Привет!")],
    max_messages=100,  # Больше сообщений
)

tasks = TaskList({
    "task_1": {"name": "Задача 1", "status": "running"},
})

# Рендерим
print(chat.render())
print(tasks.render())
```

---

## 🎬 Сценарий 6: Export чата в Markdown

```python
from modules.tui.components import ChatPanel

chat = ChatPanel(history)

def export_to_markdown():
    """Экспорт чата в Markdown."""
    
    md_lines = ["# Чат истории\n"]
    
    for role, content in chat.history:
        prefix = "**Пользователь:**" if role == "user" else "**AI-Агент**:"
        md_lines.append(f"{prefix}\n{content}\n---\n")
        
    return "\n".join(md_lines)

# Сохраняем в файл
with open("chat_history.md", "w") as f:
    f.write(export_to_markdown())
```

---

## 🎬 Сценарий 7: Multi-window режим (будущий)

```python
from modules.tui.app import TUIApp

# Создаём несколько окон
app1 = TUIApp(width=80, height=24, title="Миграция проекта A")
app2 = TUIApp(width=80, height=24, title="Миграция проекта B")
app3 = TUIApp(width=80, height=24, title="Отладка")

# Запускаем все одновременно
asyncio.create_task(app1.run())
asyncio.create_task(app2.run())
asyncio.create_task(app3.run())
```

---

## 🎬 Сценарий 8: Плагинная система виджетов (будущий)

```python
from modules.tui.app import TUIApp

class TerminalWidget:
    """Виджет встроенного терминала."""
    
    def render(self):
        return "[dim]$ python script.py[/dim]\n[green]Output...[/green]"

# Регистрируем плагин
app.register_widget("terminal", TerminalWidget())

# Добавляем в layout
app.layout.append(app.widgets["terminal"])
```

---

## 📊 Сравнение с аналогами

| Функция | Claude Code | OpenCode | J Code | Наш TUI |
|---------|--------------|----------|--------|---------|
| Чат история | ✅ | ✅ | ✅ | ✅ |
| Параллельные задачи | ✅ | ✅ | ✅ | ✅ |
| File explorer | ✅ | ✅ | ✅ | ✅ |
| Hot reload | ✅ | ✅ | ✅ | ⏳ |
| Terminal output | ✅ | ✅ | ✅ | ⏳ |
| Drag & drop | ✅ | ✅ | ✅ | ⏳ |
| Mouse events | ✅ | ✅ | ✅ | ⏳ |

**⏳ = В разработке / Будущее**
