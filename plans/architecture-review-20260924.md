# Architecture Review Report — ai-agent

> **Дата:** 2026-09-24
> **Команда:** improve-codebase-architecture

---

## Executive Summary

Кодбаза имеет сильную **трёхслойную архитектуру** (ядро → модули → промпты), но страдает от размножения мелких парсеров и монолитного конвейера в `MigrationAgent`. Основные шероховатости — дублирование функций загрузки, два независимых парсера tool-call'ов и отсутствие выделенного модуля управления задачами.

**Сила рекомендаций:** 2x Strong, 2x Worth exploring, 1x Speculative

---

## Текущая архитектура (high-level)

```
┌───────── Ядро IMMUTABLE ─────────┐
│  _core.py                         │
│  core/core_tools.py ToolRegistry  │
│  core/core.py BaseAgent+ReActEngine│
└───────────────────────────────────┘
         ↕ via importlib
┌───────── Модули MUTABLE ──────────┐
│  modules/parser.py                 │
│  modules/tracer.py TraceSession    │
│  modules/mcp_client.py MCPClient   │
└───────────────────────────────────┘
         ↕ наследники
┌─────────── Агенты ────────────────┐
│  agents/migration_agent.py (393L) │
│  agents/daily_agent.py            │
└───────────────────────────────────┘
         ↕ register_tool
┌───────── Инструменты ─────────────┐
│  core_tools.py (4 инструмента)    │
└───────────────────────────────────┘
         ↕ file_path
┌────────── Промпты ────────────────┐
│  prompts.json → prompts/*.txt     │
└───────────────────────────────────┘
```

⚠️ Два независимых парсера `<call>`: `_core.py:29` и `core/core.py:74`

---

## Кандидат #1: TaskStore — выделенный модуль управления задачами

**Рейтинг: 🔴 Strong**

### Проблема
- `MigrationAgent.execute_all()` и `_update_task_status()` читают/пишут `tasks.json` напрямую через `json.load/dump`
- Нет атомарности: сбой между read и write = повреждённый JSON
- Логика доступа к данным перемешана с логикой конвейера
- **Shallow:** интерфейс огромен (6 методов), реализация — просто read-modify-write

### Решение
Выделить **TaskStore** module с интерфейсом: `get_pending()`, `mark_completed(id)`, `mark_failed(id, reason)`. Атомарная запись через `tempfile + os.rename()`. Единый seam, за которым можно заменить JSON на SQLite/Redis.

### Выгода
- **Locality:** все баги доступа к задачам — в одном месте
- **Leverage:** любой агент использует 3 метода вместо ручного JSON
- **Testability:** один mock TaskStore — и все тесты конвейера изолированы

### Файлы
- `agents/migration_agent.py:202-306` — execute_all + _execute_single_task
- `agents/migration_agent.py:383-393` — _update_task_status
- `tasks.json` — файловый стор

### Before / After
```
Before:                    After:
MigrationAgent             MigrationAgent
    ↓ json.load/dump           ↓ get_pending/mark_*
tasks.json                TaskStore
                               ↓ atomic write
                            tasks.json
```

---

## Кандидат #2: ToolCallParser — единый парсер tool-call'ов

**Рейтинг: 🔴 Strong**

### Проблема
- `_core.py:29-62` (`execute_model_tools`) и `core/core.py:74-101` (`ReActEngine._execute_tool_call`) — **два идентичных парсера** одного формата `<call name="...">...</call>`
- Оба используют `re.search()` — находят только ПЕРВЫЙ вызов, мульти-инструментные ответы теряются
- Парсинг аргументов отличается: в `_core.py` есть special-case для `read_file_chunk`, в `core/core.py` — дублированная копия

### Решение
Выделить **ToolCallParser** в `modules/` с функцией `parse_tool_calls(text) → list[ToolCall]`. Поддержка `re.findall()` для мульти-инструментных ответов. Deletion test: если удалить один парсер, сложность не исчезнет — она в другом. Это сигнал к объединению.

### Выгода
- **Locality:** баги парсинга — в одном файле
- **Leverage:** мульти-инструменты (v2) — одно изменение
- **Testability:** один модуль тестируется изолированно от LLM

### ⚠️ Замечание
`_core.py` — immutable. Объединение потребует рефакторинга через `core/__init__.py`: импортировать новый парсер из `modules/` и заменить вызов внутри _core.py через инъекцию при загрузке пакета.

---

## Кандидат #3: PipelineExecutor — выделенный конвейер SDD→TDD→Coding→Critic

**Рейтинг: 🟡 Worth exploring**

### Проблема
- `MigrationAgent._execute_single_task()` (строки 226-306) содержит ВЕСЬ конвейер: SDD, TDD, Coding, Critic, Meta-Optimizer
- 80 строк связанной логики, которая не может быть переиспользована `DailyAgent`
- **Deletion test:** удаление этого метода не сконцентрирует сложность, а размажет её по `agent.py`

### Решение
Выделить **PipelineExecutor** module с интерфейсом: `execute(task, manifest) → bool`. Конвейер получает промпты через **PromptProvider** (seam для тестов). Каждая фаза — отдельный метод, но НЕ публичный (глубина).

### Выгода
- **Locality:** все изменения конвейера — в одном файле
- **Leverage:** можно добавить Pre-commit hook без правки MigrationAgent
- **Testability:** конвейер тестируется mock-промптами независимо от агента

---

## Кандидат #4: PromptLoader — единый загрузчик промптов

**Рейтинг: 🟡 Worth exploring**

### Проблема
- `_core.py` содержит `load_prompt()` (строка 65) и `load_prompt_from_file()` (строка 98) — код почти идентичен
- Обе читают `prompts.json`, ищут `file_path`, затем `prompt`

```
load_prompt()          vs          load_prompt_from_file()
───────────────────────────────────────────────────────────
with open(prompts.json)           with open(prompts.json)
entry = data[role_key]            entry = data[role_key]
if file_path in entry:            if file_path in entry:
    with open(entry[file_path])       with open(entry[file_path])
        return pf.read()                 return pf.read()
return entry[prompt]              return entry[prompt]
                           ^^^
                     ОДИНАКОВЫЙ КОД
```

### Решение
Оставить ОДНУ функцию с каноническим именем. Старую переименовать в `_legacy_load_prompt` с deprecation warning. В `prompts.json` добавить кэширующий декоратор (lazy load).

---

## Кандидат #5: AutoTrace — автоматический декоратор трейсинга

**Рейтинг: ⚪ Speculative**

### Проблема
- Трейсинг в `MigrationAgent` делается вручную: `self.tracer.log_llm_call()`, `self.tracer.log_tool_call()` — 6 вызовов
- Легко забыть залогировать шаг (уже были баги)
- `DailyAgent` вообще не использует трейсинг

### Решение
Создать `@trace_call(model=...)` декоратор для `call_llm()`. `TraceSession` подключается через контекстный менеджер, а не через аргументы. Декоратор логирует duration_ms, model, prompt (truncated) автоматически.

### ⚠️ Замечание
Требует изменений в core (через __init__.py). Надо проверить совместимость с hot_reload.

---

## 🏆 Топ-рекомендация

### TaskStore + ToolCallParser

Начать с этих двух — они независимы и дают максимальный эффект:

1. **TaskStore** — *deletion test* проходит: удаление ручного JSON-доступа концентрирует сложность в одном модуле
2. **ToolCallParser** — *two parsers = real seam*: дублирование кода уже доказало, что seam нужен
3. Оба не затрагивают `_core.py` (immutable) — новый код идёт в `modules/`, затем подключается через `core/__init__.py`

После них — **PipelineExecutor**, который разгрузит `MigrationAgent` (393 строки → ~150).

---

## Условные обозначения

| Рейтинг | Описание |
|---------|----------|
| 🔴 Strong | Явный дефект, исправление даёт немедленный эффект |
| 🟡 Worth exploring | Потенциально полезно, но нужен дизайн |
| ⚪ Speculative | Идея для v2, может не окупиться сейчас |

*Словарь:* **Module**, **Interface**, **Depth**, **Seam**, **Adapter** — в терминах codebase-design.