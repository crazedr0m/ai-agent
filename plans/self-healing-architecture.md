# Self-Healing Architecture

## Context

При запуске `rm -f tasks.json && ./venv/bin/python agent.py 2>&1` система падает на этапе инициализации:

```
💥 Ошибка парсинга итогового плана: Expecting value: line 1 column 1 (char 0)
❌ Не удалось инициализировать проект. Конвейер остановлен.
```

## Root Causes

### 🐛 Баг #1: Парсер не понимает ` ```json `

[`modules/parser.py:6`](../modules/parser.py:6) — `extract_code_from_markdown` ищет только ` ```python `.

[`prompts/role_global_architect1.txt:17`](../prompts/role_global_architect1.txt:17) — промпт велит выводить ` ```json `.

**Цепочка:** модель пишет ` ```json {...} ``` ` → парсер не находит ` ```python ` → возвращает `""` → `json.loads("")` → `JSONDecodeError`.

### 🐛 Баг #2: ReAct-цикл парсит JSON на любом шаге

[`initializer.py:68-95`](../initializer.py:68-95) — цикл пытается парсить JSON при **любом** ответе без инструмента, даже если модель ещё не закончила.

## Self-Healing Design

Система уже имеет Meta-Optimizer + Hot Reload в [`modules/executor.py:98-121`](../modules/executor.py:98-121), но не на этапе initializer.

### Слой 1: Локальный retry (initializer)

При ошибке парсинга JSON:
1. Если в ответе есть ` ```json ` блок, но парсер не нашёл → проблема в парсере (чиним код)
2. Если в ответе нет JSON → retry запрос к модели (возможно, модель ошиблась)
3. После N неудач → переходим к Слою 2

### Слой 2: Meta-Optimizer (универсальный recovery)

Вызываем `deepseek-r1:32b` с контекстом ошибки. Модель решает, что чинить:
- **code**: исправить код (например, modules/parser.py)
- **prompt**: исправить промпт (например, role_global_architect1.txt)

### Иерархия мутабельности

| Уровень | Файлы | Self-healing |
|---------|-------|-------------|
| **IMMUTABLE** | `core.py`, `core_tools.py` | ❌ |
| **user_approved** | `prompts/*.txt` (architect) | ✅ после спроса |
| **autonomous** | `modules/*.py`, промпты кодера/тестера | ✅ автоматически |

## Plan: 4 задачи

| # | Задача | Файл | Описание |
|---|--------|------|----------|
| 1 | **Parser: все language hints** | [`modules/parser.py:6`](../modules/parser.py:6) | Искать ЛЮБОЙ ` ```lang `, не только ` ```python ` |
| 2 | **ReAct: умный парсинг** | [`initializer.py:80-95`](../initializer.py:80-95) | Парсить JSON только если есть ` ```json `, иначе continue |
| 3 | **Self-healing Initializer** | [`initializer.py:45-98`](../initializer.py:45-98) | retry → Meta-Optimizer → патч → hot reload |
| 4 | **Self-healing Core** | [`core.py`](../core.py) + initializer | `meta_recovery()` — универсальный обработчик ошибок |