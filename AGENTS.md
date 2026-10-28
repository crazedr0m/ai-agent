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

- `venv/` — **IMMUTABLE**. Агент не имеет права её изменять или удалять.
- При разработке проекта использовать виртуальное окружение Python (`python -m venv venv && source venv/bin/activate`).
- Никакого естественного языка (промптов, инструкций) внутри Python-кода. Все промпты — в [`prompts/`](prompts/) как отдельные `.txt` файлы.
- Тесты запускаются исключительно через `subprocess.run()`. Критерий успеха — только `returncode == 0`. Поиск строковых маркеров в stdout запрещён.
- Формат вызова инструментов — **любой**, который система может обработать (XML, JSON, tool_call native). См. [`ADR-001`](docs/adr/ADR-001-core-boundaries.md).

## 🔧 Зоны мутабельности (см. [`ADR-001`](docs/adr/ADR-001-core-boundaries.md))

| Зона | Файлы | Правило |
|------|-------|---------|
| **supervised** | [`_core.py`](_core.py), [`core/core.py`](core/core.py), [`core/core_tools.py`](core/core_tools.py), [`core/__init__.py`](core/__init__.py) | Изменения требуют подтверждения человека (y/n) |
| **autonomous** | [`core_tools.py`](core_tools.py) (корень), `agents/*.py`, `modules/*.py`, `prompts/*.txt`, [`prompts.json`](prompts.json) | Агент может менять самостоятельно (с учётом флага `mutability` в prompts.json) |
| **kernel** | *(пока пусто)* | Только человек. Добавление файла — через новый ADR |

## 🔧 Неочевидные детали архитектуры

- [`_core.py:15`](_core.py:15) жёстко зашивает `OLLAMA_URL = "http://192.168.5.7:11434/api/generate"` — это не конфиг, а константа.
- Модели: `qwen2.5-coder:14b` (default), `qwen3-coder:30b` (архитектор/SDD), `deepseek-r1:32b` (мета-оптимизация промптов).
- [`_core.py:147`](_core.py:147) использует `os.execv()` для hot reload — процесс перезапускается в памяти.
- [`prompts.json`](prompts.json) содержит два типа записей: с inline `prompt` и с `file_path` в `prompts/`. Это два разных механизма загрузки.
- [`core/__init__.py`](core/__init__.py) проксирует атрибуты из `_core.py` в пакет `core`, чтобы `import core` продолжал работать.
- `execute_model_tools()` в `_core.py` **удалён** (был дублём `ReActEngine.execute_tool_call` в `core/core.py`).

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

Все зависимости объявлены в [`pyproject.toml`](pyproject.toml) (единый источник правды,
`requirements.txt` удалён). Runtime: `requests`, `rich`, `python-dotenv`, `mcp`, `fastmcp`,
`tree-sitter` (+ грамматики). Dev (`coverage`) — в `[project.optional-dependencies].dev`.
Никаких дев-зависимостей в runtime-списке (pytest, flake8, mypy и т.д.).
Проект ставится как пакет: `pip install -e .` (или `pip install -e ".[dev]"`).

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