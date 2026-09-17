# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## 🧠 Project Identity

**Autonomous AI Software Engineer v1.0** — мультиагентная система для автономной миграции легаси-кода. Работает полностью локально через Ollama.

## 🚫 Критические правила (нарушение = поломка системы)

- [`core.py`](core.py) и [`core_tools.py`](core_tools.py) — **IMMUTABLE**. Агент не имеет права их изменять.
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
```

## 📦 Зависимости

Только `requests` и `rich` (см. [`requirements.txt`](requirements.txt)). Никаких дев-зависимостей (pytest, flake8, mypy и т.д.).

## 🔥 Mutability промптов

В [`prompts.json`](prompts.json) флаг `mutability`:
- `immutable` — запрещено менять
- `user_approved` — требует подтверждения человека (y/n)
- `autonomous` — агент может менять самостоятельно