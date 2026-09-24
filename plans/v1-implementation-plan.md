# План v1 — Рефакторинг архитектуры + трейсинг + MCP

## Структура директорий (целевая)

```
ai-agent/
├── core/
│   ├── core.py              # Ядро + BaseAgent + ReActEngine
│   └── core_tools.py         # Инструменты + @register_tool
├── agents/
│   ├── migration_agent.py    # Текущий конвейер SDD→TDD→Coding
│   └── daily_agent.py        # Базовый ReAct-ассистент (v1 заготовка)
├── modules/
│   ├── tracer.py             # Трейсинг (JSONL, ротация)
│   ├── mcp_client.py         # MCP-клиент (HTTP/SSE)
│   └── parser.py             # Существующий, доработанный
├── traces/                   # Сессии трейсов
├── prompts/                  # Промпты (как есть)
├── initializer.py            # Тонкая обёртка → migration_agent
├── executor.py               # Удаляется / вливается в migration_agent
├── test_core.py              # Существующий + новые тесты
├── prompts.json              # Как есть
├── requirements.txt          # + mcp, pytest, pytest-mock
├── .env.example
└── CONTEXT.md                # Создан
```

## Тикеты реализации (с блокирующими связями)

```
T1. [core] BaseAgent + ReActEngine         ← СТАРТ
  ↓ блокирует всё, что ниже
T2. [core] @register_tool декоратор         ← можно параллельно с T1
  ↓ блокирует T3
T3. [core] Инструменты на декораторах      ← миграция существующих
  ↓
T4. [modules] Tracer (tracer.py)           ← можно параллельно с T2-T3
  ↓ (нужен для тестирования агентов)
T5. [agents] MigrationAgent               ← блокирует удаление initializer+executor
  ↓
T6. [agents] DailyAgent (заготовка)       ← независим от T5
  ↓
T7. [modules] MCP-клиент (mcp_client.py)   ← независим от T5-T6
  ↓
T8. [config] .env + валидация             ← финальная полировка
T9. [tests] Интеграционные тесты           ← после T1-T8
T10.[cleanup] Удаление executor.py        ← после T5
```

## Приоритеты выполнения

### Priority 0: Базовый костяк (можно начинать)

| Тикет | Файл | Описание |
|---|---|---|
| T1 | `core/core.py` | Добавить `BaseAgent(ABC)` с `run()`, `ReActEngine` как внутренний цикл |
| T2 | `core/core_tools.py` | Добавить `@register_tool(name, description)` декоратор |
| T4 | `modules/tracer.py` | Создать модуль трейсинга: `TraceSession`, `StepTrace`, JSONL-запись, ротация |

**Блокировки**: T3 ждёт T2. T5 ждёт T1+T4.

### Priority 1: Миграция на новую архитектуру

| Тикет | Файл | Описание |
|---|---|---|
| T3 | `core/core_tools.py` | Перевести `list_dir`, `view_file_outline`, `read_file_chunk`, `query_db_schema` на декораторы |
| T5 | `agents/migration_agent.py` | Перенести логику из `initializer.py` + `executor.py` в `MigrationAgent(BaseAgent)` |
| T10 | `initializer.py` | Переписать как тонкую обёртку, вызывающую `MigrationAgent` |

### Priority 2: Новый функционал

| Тикет | Файл | Описание |
|---|---|---|
| T6 | `agents/daily_agent.py` | `DailyAgent(BaseAgent)` — минимальный ReAct: вопросы по коду, read_file/list_dir/search |
| T7 | `modules/mcp_client.py` | MCP-клиент: SSE-подключение, получение инструментов, регистрация в ToolRegistry |

### Priority 3: Инфраструктура

| Тикет | Файл | Описание |
|---|---|---|
| T8 | `.env.example`, `initializer.py` | Валидация Ollama endpoint, конфиг ротации трейсов |
| T9 | `test_*.py` | pytest-тесты: BaseAgent (mocked LLM), инструменты, Tracer, MCP-client (mocked) |
| T10 | — | Удалить `executor.py`, проверить что всё работает |

## Диаграмма зависимостей

```mermaid
flowchart TD
    T1[BaseAgent + ReActEngine] --> T5[MigrationAgent]
    T1 --> T6[DailyAgent]
    T2[@register_tool] --> T3[Миграция инструментов]
    T4[Tracer] --> T5
    T4 --> T6
    T3 --> T5
    T3 --> T7[MCP-клиент]
    T5 --> T10[cleanup executor.py]
    T1 --> T8[config + .env]
    T2 --> T8
    T1 --> T9[тесты]
    T2 --> T9
    T4 --> T9
```

## Что отложено на v2 (зафиксировано в Not yet specified)

- **MCP-генератор** (агент пишет свои MCP-серверы)
- **Ретроспективы по трейсам** (анализ сессий, self-improvement промптов)
- **Meta-агент** (оркестрация между MigrationAgent и DailyAgent)
- **Улучшение парсера** (regex-парсер для ReAct вызовов)
- **Self-extension** (агент пишет новые модули)
- **RAG по трейсам**
- **Meta-cognition** (анализ архитектуры)

## Критерии готовности v1

1. `BaseAgent` в core.py, `MigrationAgent` работает через него (ReAct-цикл)
2. Все инструменты зарегистрированы через `@register_tool`
3. Трейсы пишутся в `traces/session_<timestamp>/` в JSONL-формате
4. `DailyAgent` отвечает на вопросы по коду с инструментами
5. MCP-клиент подключается к Web fetch и Filesystem серверам
6. `initializer.py` — тонкая обёртка
7. `executor.py` удалён
8. `pytest` покрытие: BaseAgent (mocked LLM), инструменты, Tracer, MCP-клиент
9. `.env.example` с валидацией Ollama endpoint