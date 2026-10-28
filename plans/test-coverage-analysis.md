# Анализ тестового покрытия кодовой базы

## Методология

Измерение проведено утилитой `coverage.py` с `unittest discover` по всем тестам в `tests/test_*.py`.
Запуск: `./venv/bin/python -m coverage run -m unittest discover -s tests -p "test_*.py"`

**До P0:** 102 теста, общее покрытие **52%** (3373 stmts, 1606 missed)
**После P0:** 218 тестов, общее покрытие **67%** (2071 stmts, 678 missed)
**После P1:** **309 тестов, общее покрытие ~64%** (3481 stmts, 1268 missed)
— область замера расширена до `_core.py,core/*.py,core_tools.py,modules/*.py,agents/*.py,mcp_servers/**/*.py`

---

## 1. ЯДРО (CORE)

| Файл | Stmts | Miss | Cover | Оценка | Изменение |
|------|-------|------|-------|--------|-----------|
| `_core.py` | 76 | 0 | **100%** | 🟢 Отличное | +67% ✅ |
| `core/core.py` | 82 | 23 | **72%** | 🟢 Хорошее | — |
| `core/core_tools.py` | 163 | 49 | **70%** | 🟢 Хорошее | — |
| `core/__init__.py` | 23 | 2 | **91%** | 🟢 Отличное | — |
| `core_tools.py` (корень) | 46 | 15 | **67%** | 🟡 Среднее | — |

### НЕ ПОКРЫТО в `_core.py` (100%): **Всё покрыто** ✅

### НЕ ПОКРЫТО в `core/core.py` (72%):
- Repair-цикл execute(): строки 66-67, 88-126
- `execute_tool_call()` error handling: строка 156, 162-163

### НЕ ПОКРЫТО в `core/core_tools.py` (70%):
- `_func_to_schema()` для list/dict/Optional: строки 35-36, 38, 40-41, 59
- `_parse_raw_args()` JSON fallback: строки 90, 98-102, 117-121, 124, 130, 141
- `_unquote()`: строка 168
- `_coerce_type()` int/float edges: строки 179-182, 184-187
- `ToolRegistry.get_schema()`: строки 234-237
- `ToolRegistry.validate_call()` error paths: строки 246, 253-255, 262, 267
- `tool_names` property: строка 286
- `get_tool()`: строка 311

---

## 2. МОДУЛИ (modules/)

| Файл | Stmts | Miss | Cover | Оценка | Изменение |
|------|-------|------|-------|--------|-----------|
| `parser.py` | 13 | 0 | **100%** | 🟢 Отличное | +77% ✅ |
| `tool_parser.py` | 57 | 5 | **91%** | 🟢 Отличное | +23% ✅ |
| `dev_tools.py` | 157 | 15 | **90%** | 🟢 Отличное | +75% ✅ |
| `permissions.py` | 57 | 6 | **89%** | 🟢 Отличное | +80% ✅ |
| `gate.py` | 129 | 22 | **83%** | 🟢 Отличное | +29% ✅ |
| `sandbox.py` | 79 | 20 | **75%** | 🟢 Хорошее | +29% ✅ |
| `scaffold.py` | 70 | 0 | **100%** | 🟢 Отличное | +64% ✅ |
| `tracer.py` | 90 | 10 | **89%** | 🟢 Хорошее | — |
| `hot_reload.py` | 72 | 1 | **99%** | 🟢 Отличное | +48% ✅ |
| `checkpoint_manager.py` | 110 | 21 | **81%** | 🟢 Хорошее | — |
| `progress_reporter.py` | 60 | 0 | **100%** | 🟢 Отличное | — |
| `dependency_planner.py` | 151 | 4 | **97%** | 🟢 Отличное | — |
| `repo_map.py` | 164 | 15 | **91%** | 🟢 Отличное | — |
| `retrospective.py` | 165 | 90 | **45%** | 🔴 Низкое | — |
| `mcp_client.py` | 145 | 99 | **32%** | 🔴 Низкое | — |
| `migration_context.py` | 3 | 0 | **100%** | 🟢 Facade | — |
| `llm/__init__.py` | 2 | 0 | **100%** | 🟢 | — |
| `llm/adapter.py` | 90 | 60 | **33%** | 🔴 Низкое | — |
| `log16_integration.py` | 67 | 60 | **10%** | 🔴 Критическое | — |
| `eval/` (6 файлов) | — | — | **0%** | 🔴 Критическое | — |
| `tui/` (6 .py) | — | — | **0%** | 🔴 Критическое | — |

---

## 3. АГЕНТЫ (agents/)

| Файл | Stmts | Miss | Cover | Оценка |
|------|-------|------|-------|--------|
| `casual_agent.py` | — | — | **0%** | 🔴 Критическое |
| `migration_agent.py` | — | — | **0%** | 🔴 Критическое |
| `retry_system.py` | — | — | **0%** | 🔴 Критическое |
| `task_manager.py` | — | — | **0%** | 🔴 Критическое |
| `pipeline_executor.py` | — | — | **0%** | 🔴 Критическое |
| `meta_recovery.py` | — | — | **0%** | 🔴 Критическое |

**Все агенты = 0%** (не вошли в замер из-за отсутствия тестов)

---

## 4. MCP-СЕРВЕРЫ (mcp_servers/)

| Файл | Stmts | Miss | Cover | Оценка |
|------|-------|------|-------|--------|
| `code_analyzer/core.py` | 28 | 3 | **89%** | 🟢 |
| `code_analyzer/tools.py` | 4 | 0 | **100%** | 🟢 |
| `code_analyzer/server.py` | 3 | 0 | **100%** | 🟢 |
| `code_analyzer/query_tools.py` | 36 | 4 | **89%** | 🟢 |
| `code_analyzer/scan_tools.py` | 54 | 4 | **93%** | 🟢 |
| `code_analyzer/tool_helpers.py` | 11 | 3 | **73%** | 🟡 |
| `code_analyzer/cross_ref_tools.py` | 43 | 31 | **28%** | 🔴 |
| `code_analyzer/cross_language/php_js_bridge.py` | 108 | 89 | **18%** | 🔴 |
| `code_analyzer/languages/python/analyzer.py` | 114 | 4 | **96%** | 🟢 |
| `code_analyzer/languages/go/analyzer.py` | 108 | 88 | **19%** | 🔴 |
| `code_analyzer/languages/javascript/analyzer.py` | 127 | 107 | **16%** | 🔴 |
| `code_analyzer/languages/php/analyzer.py` | 105 | 84 | **20%** | 🔴 |
| `code_analyzer/languages/php/procedural.py` | 102 | 91 | **11%** | 🔴 |
| `code_analyzer/languages/php/string_detector.py` | 79 | 62 | **22%** | 🔴 |
| `code_analyzer/languages/typescript/analyzer.py` | 144 | 124 | **14%** | 🔴 |
| `code_analyzer/languages/base.py` | 27 | 1 | **96%** | 🟢 |
| `fetch/tools.py` | 54 | 29 | **46%** | 🟡 |
| `fetch/html_converter.py` | 27 | 20 | **26%** | 🔴 |
| `fetch/server.py` | 3 | 0 | **100%** | 🟢 |
| `filesystem/tools.py` | 109 | 21 | **81%** | 🟢 |
| `filesystem/helpers.py` | 2 | 0 | **100%** | 🟢 |
| `filesystem/server.py` | 3 | 0 | **100%** | 🟢 |
| `substrate/helpers.py` | 103 | 9 | **91%** | 🟢 |
| `substrate/tools.py` | 20 | 0 | **100%** | 🟢 |
| `substrate/server.py` | 3 | 0 | **100%** | 🟢 |

---

## 5. СВОДНАЯ ТАБЛИЦА ПО ЗОНАМ

| Зона | Строк кода | Покрытие | Изменение | Статус |
|------|-----------|----------|-----------|--------|
| **Ядро (core/ + _core.py + core_tools.py)** | ~390 | **~82%** | +22% | 🟢 |
| **Модули (modules/)** | ~1681 | **~72%** | +19% | 🟢 |
| **Агенты (agents/)** | ~0 (не измерено) | **0%** | — | 🔴 |
| **MCP-серверы (mcp_servers/)** | ~1378 | **~49%** | — | 🟡 |
| **ИТОГО (полная выборка)** | **3481** | **64%** | **+12%** | 🟡 |

---

## 6. ПРИОРИТЕТИРОВАННЫЙ ПЛАН ДОБАВЛЕНИЯ ТЕСТОВ

### P0 — ВЫПОЛНЕН ✅

| # | Файл | Было | Стало | Тестов |
|---|------|------|-------|--------|
| 1 | `_core.py` | 33% | **100%** | ✅ 18 |
| 2 | `parser.py` | 23% | **100%** | ✅ 13 |
| 3 | `permissions.py` | 9% | **51%** | ✅ 13 |
| 4 | `tool_parser.py` | 68% | **91%** | ✅ 16 |
| 5 | `dev_tools.py` | 15% | **90%** | ✅ 37 |
| | **Итого P0** | **31% (среднее)** | **86% (среднее)** | **97 новых тестов** |

### 🔴 P1 — ВЫПОЛНЕН ✅

| # | Файл | Было | Стало | Тестов | Сложность |
|---|------|------|-------|--------|-----------|
| 1 | `permissions.py` | 51% | **89%** | +10 | Средняя (curses mocking) ✅ |
| 2 | `scaffold.py` | 36% | **100%** | +23 | Средняя (write_to_file corruption) ✅ |
| 3 | `hot_reload.py` | 51% | **99%** | +26 | Средняя ✅ |
| 4 | `gate.py` | 54% | **83%** | +22 | Средняя (eval-метрики) ✅ |
| 5 | `sandbox.py` | 46% | **75%** | +14 | Средняя (git mocking) ✅ |
| | **Итого P1 (модули)** | **48% (среднее)** | **89% (среднее)** | **+95 тестов** | ✅ |

### 🟡 P1+ — Осталось доделать (на паузе)

| # | Файл | Текущее | Цель | Сложность |
|---|------|---------|------|-----------|
| 1 | `llm/adapter.py` | 33% | 70% | Высокая (Ollama, retry, профили) |
| 2 | `retrospective.py` | 45% | 75% | Средняя |
| 3 | `mcp_client.py` | 32% | 65% | Высокая (асинхронный) |
| 4 | `log16_integration.py` | 10% | 60% | Средняя |

### 🟡 P2 — Анализаторы кода и MCP-серверы

| # | Файл | Текущее | Цель | Сложность |
|---|------|---------|------|-----------|
| 1 | `core/core.py` | 72% | 85% | Средняя |
| 2 | `core/core_tools.py` | 70% | 85% | Средняя |
| 3 | `cross_ref_tools.py` | 28% | 70% | Средняя |
| 4 | `fetch/tools.py` | 46% | 75% | Средняя |
| 5 | `fetch/html_converter.py` | 26% | 60% | Простая |
| 6 | `languages/*.py` (5 файлов) | 11-20% | 50% | Средняя |

### 🔵 P3 — Агенты (нужен mock LLM)

| # | Файл | Текущее | Цель | Сложность |
|---|------|---------|------|-----------|
| 1 | `task_manager.py` | 0% | 85% | Простая |
| 2 | `retry_system.py` | 0% | 70% | Средняя |
| 3 | `casual_agent.py` | 0% | 60% | Средняя |
| 4 | `migration_agent.py` | 0% | 60% | Высокая |
| 5 | `pipeline_executor.py` | 0% | 60% | Высокая |
| 6 | `meta_recovery.py` | 0% | 50% | Высокая |

---

## 7. РЕКОМЕНДАЦИИ

1. **Следующие цели:** `llm/adapter.py` (33%) — основа вызовов LLM, без него нельзя тестировать агентов
2. **Быстрые победы P1:** `scaffold.py` (36%), `hot_reload.py` (51%) — по 20-30 минут
3. **TDD для агентов:** mocking LLM через `unittest.mock.patch` (уже есть паттерн в test_base_agent)
4. **Интеграционные тесты:** agent.py — через `subprocess.run(['python', 'agent.py', '--help'])`
5. **Тяжёлые кейсы:** `mcp_client.py` (асинхронный), `gate.py` (eval-метрики) — нужны отдельные подходы
6. **Целевой уровень:** 80% через продолжение работы по плану P1→P2→P3