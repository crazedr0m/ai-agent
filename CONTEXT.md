# CONTEXT.md — Доменная модель ai-agent

## Термины

### Agent (Агент)
Конкретный режим работы системы, наследующий `BaseAgent`. Определяет системный промпт, набор инструментов и поведение на каждом шаге ReAct-цикла. Примеры: MigrationAgent, CasualAgent.

### BaseAgent (Базовый Агент)
Абстрактный класс в ядре, реализующий общий алгоритм ReAct-цикла. Подклассы переопределяют `get_system_prompt()`, `get_tools()`, `on_step_completed()`.

**✅ Улучшение №1:** `max_steps` теперь настраивается через манифест (по умолчанию 10).

**🔄 Улучшение №2:** MigrationAgent поддерживает параллельное выполнение задач через `asyncio.gather()`.

### ReActEngine (ReAct-движок)
Цикл модели: LLM → парсинг вызова → выполнение инструмента → запись трейса → повтор. Инкапсулирован в `BaseAgent.run()`.

**✅ Улучшение №1:** `max_steps` — настраиваемый лимит шагов (по умолчанию 10, может быть задан через манифест).

### ToolRegistry (Реестр инструментов)
Механизм регистрации инструментов через декоратор `@register_tool`. Каждый инструмент имеет имя, описание, функцию и мета-информацию для автодокументирования и MCP-экспорта.

### Tracer (Трейсер)
Модуль, записывающий каждый шаг ReAct-цикла в JSONL-файл в `traces/session_<timestamp>/`. Хранит до 50 сессий с ротацией.

### MCPClient
Клиент для подключения к внешним MCP-серверам по протоколу Model Context Protocol (HTTP/SSE). Получает список инструментов сервера и регистрирует их в ToolRegistry.

### SessionTrace (Трейс сессии)
Папка `traces/session_<timestamp>/` с набором JSONL-файлов: `metadata.jsonl`, `step_NNN.jsonl`, `summary.jsonl`.

### StepTrace (Трейс шага)
Один шаг ReAct-цикла: входной промпт, ответ LLM, распарсенный вызов инструмента, результат выполнения, флаг ошибки.

### Core (Ядро)
Загрузчик и цикл исполнения. Состоит из supervised-файлов ([`_core.py`](_core.py) — низкоуровневые функции, [`core/core.py`](core/core.py) — BaseAgent + ReActEngine, [`core/core_tools.py`](core/core_tools.py) — ToolRegistry) и autonomous-файла [`core_tools.py`](core_tools.py) (реализации инструментов). См. [`ADR-001`](docs/adr/ADR-001-core-boundaries.md).

### Migration Agent
Агент миграции легаси-кода (текущий конвейер SDD → TDD → Coding). Наследует BaseAgent.

**🔄 Улучшение №2:** Поддерживает параллельное выполнение задач через `asyncio.gather()`. Методы:
- `execute_all_parallel()` — параллельный конвейер для всех pending задач
- `_execute_single_task_async()` — асинхронное выполнение одной задачи (SDD → TDD → Coding → Tests → Critic)

### Daily Agent (Ежедневный ассистент)
Повседневный ассистент разработчика: отвечает на вопросы по коду с использованием инструментов.

### Meta Agent (Мета-агент)
Агент саморазвития: анализирует трейсы, улучшает промпты, пишет новые модули. (v2+)

### Code Analyzer (Статический анализатор кода)
MCP-сервер на базе Tree-sitter, реализующий мультиязычный статический анализ. Единый FastMCP-процесс с языковыми модулями. См. [ADR-002](docs/adr/ADR-002-multi-language-analyzer.md).

### BaseAnalyzer (Базовый анализатор языка)
Абстрактный класс в `mcp_servers/code_analyzer/languages/base.py`. Определяет интерфейс для языкового модуля:
- `collect_definitions()` — функции, классы, импорты, вызовы
- `get_symbol_signature()` — сигнатура символа
- `build_call_graph()` — граф вызовов внутри файла

Каждый язык реализует свой подкласс.

### PHP→JS Bridge (PHP→JS мост)
Механизм cross-language анализа: детекция строковых литералов в PHP → распознавание HTML/JS/CSS-фрагментов → изоляция и парсинг JS-кода → резолвинг символов в .js-файлах. Реализован в `mcp_servers/code_analyzer/cross_language/php_js_bridge.py`.

### Cross-language Graph (Межъязыковой граф вызовов)
Совмещённый граф вызовов, объединяющий AST-данные из нескольких языков. Для PHP-файла показывает также JS-символы, найденные в строковых литералах, с указанием файла-источника (.js).

### Fractional Layered Memory (Дробно-слойная память)
MCP-сервер долговременной памяти агента: факты хранятся узлами и раскладываются по слоям (band) по дробно-логарифмической шкале. Реализован в `mcp_servers/fractional_memory/`. Инструменты: `write_fact`, `query_facts`, `consolidate_memory`; ресурс `memory://bands`.

### Fractional Cache (Дробно-логарифмический кэш)
Принцип организации памяти: положение факта определяется дробно-логарифмической шкалой по возрасту и частоте доступа, а не линейным кэшем. Отражён в формуле пересчёта слоя в [`MemoryNode.recalculate_band()`](mcp_servers/fractional_memory/helpers.py:58).

### Band (Слой памяти)
Одна из 16 полос хранения факта (0–15). Band 15 (Core) — статические правила, всегда доступны; Bands 1–14 — ассоциативные факты по gate_trigger; Band 0 (Spike) — быстрозабывающийся контекст.

### MemoryNode (Узел памяти)
Единица хранения дробно-слойной памяти: `payload`, `gate_trigger`, `frequency_band`, `access_count`, `last_accessed`. Определён в [`mcp_servers/fractional_memory/helpers.py`](mcp_servers/fractional_memory/helpers.py:27).

### FractionalMemory (Интеграция памяти)
Модуль-мост между конвейером миграции и MCP-сервером памяти: записывает факты о задачах, загружает контекст прошлых сессий, финализирует миграцию. Реализован в [`modules/fractional_memory.py`](modules/fractional_memory.py:5).