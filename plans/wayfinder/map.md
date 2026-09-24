# wayfinder:map — Эволюция ai-agent в универсальный мультиагентный инструмент

## Destination

Переход от monolith-конвейера миграции легаси к модульной мультиагентной архитектуре с саморазвитием (self-healing → self-improvement → self-extension → meta-cognition). v1: рефакторинг ядра + трейсинг + MCP-клиент. Путь ясен, когда `core/core.py` содержит абстрактный `BaseAgent`, `MigrationAgent` работает через него, `DailyAgent` даёт базовый ReAct, а трейсы пишутся в `traces/`.

## Notes

- **Домен**: эволюция существующей кодовой базы, не переписывание
- **Язык**: Python 3.10+
- **LLM**: Ollama (qwen2.5-coder:14b default, qwen3-coder:30b для архитектуры, deepseek-r1:32b для мета-оптимизации)
- **Архитектура**: core/ (неизменяемое ядро) + agents/ (режимы работы) + modules/ (переиспользуемые модули)
- **Тестирование**: pytest + pytest-mock, LLM замокана, инструменты — на реальных файлах
- **Трейсинг**: JSONL, `traces/session_<timestamp>/step_NNN.jsonl`, ротация 50 сессий
- **ReAct-движок**: общий `BaseAgent` в ядре с интерфейсом для инъекций
- **Инструменты**: `@register_tool` декоратор с метаданными, TOOLS_MAP остаётся как бекенд

## Decisions so far

- [Эволюция или переписывание](plans/wayfinder/tickets/T1-evolution-vs-rewrite.md): **Эволюция**. Текущая кодовая база расширяется новыми модулями, ядро дорабатывается.
- [Определение саморазвития](plans/wayfinder/tickets/T2-self-development-definition.md): **4 уровня**: self-healing → self-improvement → self-extension → meta-cognition. Последовательно.
- [MCP: потребление или создание](plans/wayfinder/tickets/T3-mcp-scope.md): **Сначала клиент** (v1), создание MCP-серверов — v2.
- [Целевая аудитория](plans/wayfinder/tickets/T4-target-audience.md): **Персональный инструмент** (с расширяемой архитектурой).
- [Приоритет сценариев](plans/wayfinder/tickets/T5-scenarios-priority.md): **Оба равнозначны** — миграция как один из режимов + daily dev assistant.
- [Архитектура core/agents/modules](plans/wayfinder/tickets/T6-architecture-layers.md): **Трёхслойная**: core неизменяемое ядро, agents режимы работы, modules переиспользуемые компоненты.
- [ReAct-движок](plans/wayfinder/tickets/T7-react-engine-design.md): **Абстрактный BaseAgent** в ядре с общим алгоритмом, конкретные агенты через интерфейс.
- [Декораторная регистрация инструментов](plans/wayfinder/tickets/T8-tool-registration.md): **Да**, `@register_tool` с метаданными, с тестовым покрытием.
- [Формат трейсинга](plans/wayfinder/tickets/T9-trace-format.md): **JSONL**, `traces/session_<timestamp>/`, отдельный файл на шаг, ротация 50 сессий в конфиге.
- [MCP-серверы для v1](plans/wayfinder/tickets/T10-mcp-servers-v1.md): **Web fetch MCP** и **Filesystem MCP**.
- [Итерации v1/v2/v3](plans/wayfinder/tickets/T11-iteration-plan.md): **v1** ядро+трейсинг+MCP-клиент, **v2** MCP-генератор+ретроспективы, **v3** self-extension+meta-cognition.

## Not yet specified

- **Детали мета-агента (v2-v3)**: как именно агент будет анализировать трейсы и улучшать промпты. Алгоритм ретроспективы пока не спроектирован.
- **Архитектура MCP-генератора (v2)**: как агент будет писать и деплоить MCP-серверы. Язык, шаблоны, рантайм — не определены.
- **Self-extension механизм (v3)**: как агент будет писать новые модули для самого себя. Ограничения безопасности, CI для самогенерируемого кода.
- **RAG по трейсам (v3)**: векторизация и поиск по прошлым сессиям. Инфраструктура (векторная БД) — не выбрана.
- **Meta-cognition (v3)**: анализ архитектуры системы самим агентом и предложение изменений.

## Out of scope

- **Миграция на другую LLM-инфраструктуру** (не Ollama) — не планируется.
- **Web UI / дашборд** — агент работает через CLI.
- **Multi-tenant / авторизация** — персональный инструмент.
- **Смена языка с Python** — весь стек на Python.