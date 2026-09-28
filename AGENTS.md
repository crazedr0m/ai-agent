# AGENTS.md (Часть 18)

This file provides guidance to agents when working with code in this repository.

## 🧠 Project Identity

**Autonomous AI Software Engineer v1.0** — мультиагентная система для автономной миграции легаси-кода. Работает полностью локально через Ollama.

## ✅ Архитектурные улучшения (Вариант А)

### Улучшение №1: Настраиваемый `max_steps` ✅
- `max_steps` теперь настраивается через [`migration_manifest.json`](migration_manifest.json) в секции `react_config`
- Hard-coded лимит удалён из всех агентов
- По умолчанию: 10 шагов

### Улучшение №2: Параллельное выполнение задач ✅ (NEW!)
- `execute_all()` заменён на `execute_all_parallel()` с использованием `asyncio.gather()`
- Все pending задачи выполняются параллельно вместо последовательного выполнения
- Обработка исключений через `return_exceptions=True`
- Промпты и LLM вызовы асинхронизируются через `asyncio.to_thread()`

### Улучшение №3: Shared context между этапами конвейера ✅ (NEW!)
- Каждый этап (SDD → TDD → Coding) сохраняет данные в `shared_context.json`
- SDD документ передаётся в TDD, а затем в Coding
- Тесты передаются из TDD в Coding
- Critic и Meta-Optimizer получают полный контекст всех предыдущих шагов
- Глобальный счётчик выполненных задач для мониторинга прогресса

### Улучшение №4: Система восстановления после ошибок ✅ (NEW!)
- Реализован `RetrySystem` в [`agents/retry_system.py`](agents/retry_system.py)
- Стратегия эскалации:
  - **Retry**: до 3 попыток с задержкой
  - **Escalation Level 1**: повышение приоритета задачи
  - **Escalation Level 2**: Critic review (анализ ошибки)
  - **Escalation Level 3**: Meta-Optimizer (переписывание промптов + hot reload)
- Интеграция через `execute_task_with_retry()`
- ✅ Синтаксическая ошибка в `migration_agent.py` исправлена

## 🚫 Критические правила (нарушение = поломка системы)

- [`core.py`](core.py) и [`core_tools.py`](core_tools.py) — **IMMUTABLE**. Агент не имеет права их изменять.
- Папка `venv/` — **IMMUTABLE**. Агент не имеет права её изменять или удалять.
- При разработке проекта использовать виртуальное окружение Python (`python -m venv venv && source venv/bin/activate`).
- Никакого естественного языка (промптов, инструкций) внутри Python-кода. Все промпты — в [`prompts/`](prompts/) как отдельные `.txt` файлы.
- Тесты запускаются исключительно через `subprocess.run()`. Критерий успеха — только `returncode == 0`. Поиск строковых маркеров в stdout запрещён.
- Вызов инструментов модели — строго через XML-теги `<call name="tool_name">args</call>`, НЕ через JSON.

## 🔧 Неочевидные детали архитектуры

- [`core.py`](core.py:14) жёстко зашивает `OLLAMA_URL = "http://192.168.5.7:11434/api/generate"` — это не конфиг, а константа.
- Модели: `qwen2.5-coder:14b` (default), `qwen3-coder:30b` (архитектор/SDD), `deepseek-r1:32b` (мета-оптимизация промптов).
- [`core.py`](core.py:109) использует `os.execv()` для hot reload — процесс перезапускается в памяти.
- [`prompts.json`](prompts.json) содержит два типа записей: с inline `prompt` и с `file_path` в `prompts/`. Это два разных механизма загрузки.

## 🏗️ Конвейер выполнения

```
manifest.json → Global Architect (создаёт tasks.json)
  → SDD (архитектурный план, 30B модель)
    → TDD (генерация тестов ДО кода)
      → Coding (написание реализации)
        → Тесты (returncode проверка)
          → Успех → следующая задача
          → Провал → Critic (до 3 попыток)
            → Тупик → Meta-Optimizer → перезапись prompts/ → Hot Reload

🔄 Параллельное выполнение: все pending задачи выполняются одновременно через asyncio.gather()
🔄 Retry с эскалацией: при ошибке задача проходит retry → escalation pipeline
```

## 📦 Зависимости

Только `requests` и `rich` (см. [`requirements.txt`](requirements.txt)). Никаких дев-зависимостей (pytest, flake8, mypy и т.д.).

## 🔥 Mutability промптов

В [`prompts.json`](prompts.json) флаг `mutability`:
- `immutable` — запрещено менять
- `user_approved` — требует подтверждения человека (y/n)
- `autonomous` — агент может менять самостоятельно

## Agent skills

### Issue tracker

Issues live in GitHub Issues (repo: `crazedr0m/ai-agent`). See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical triage roles are used with their default names. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout. See `docs/agents/domain.md`.