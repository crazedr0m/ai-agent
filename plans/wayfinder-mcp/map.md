# wayfinder:map — MCP-серверы для концепции «Субстрат» (статический анализатор + LOG16)

## Destination

Спецификация и архитектурный план для двух независимых MCP-серверов, реализующих концепцию «Субстрат»: статический анализатор кода на базе Tree-sitter и динамическая multi-frequency ассоциативная память LOG16. Путь ясен, когда зафиксированы: API обоих серверов, формат данных, схема интеграции с ai-agent через mcp_client.py, и план итераций v1/v2/v3.

## Notes

- **Домен**: создание MCP-серверов с нуля (отдельный проект, не эволюция существующей кодовой базы)
- **Язык**: Python 3.10+, FastMCP SDK
- **Связка**: два независимых MCP-сервера, объединённых через mcp_client.py
- **Статический анализатор**: Tree-sitter (Python-биндинги), Python-only v1
- **LOG16**: MemoryNode + 16 log-полос + write/query/equalize + status resource (v1)
- **Формат данных**: JSON (канонический) + Markdown (MCP-ресурс для чтения моделью)
- **Интеграция**: mcp_client.py из основного wayfinder-плана ai-agent
- **Тестирование**: на этапе реализации

## Decisions so far

<!-- the index: one line per closed ticket -->

## Tickets

### Research (AFK — можно запускать параллельно)

- [R1 — Исследование Tree-sitter Python API](plans/wayfinder-mcp/tickets/R1-tree-sitter-research.md): установка, AST, граф вызовов, сигнатуры, ограничения
- [R2 — Исследование первоисточника LOG16/SUBTRAT](plans/wayfinder-mcp/tickets/R2-log16-original-research.md): оригинальные посты Техножнеца, сравнение с docs/log16.md
- [R3 — Исследование FastMCP SDK](plans/wayfinder-mcp/tickets/R3-fastmcp-research.md): инструменты, ресурсы, транспорт, best practices

### Grilling (HITL — требуют обсуждения)

- [G1 — Архитектура статического анализатора](plans/wayfinder-mcp/tickets/G1-analyzer-architecture.md): что парсить, формат графа, MCP-инструменты/ресурсы, кэширование
- [G2 — LOG16 v1 API Specification](plans/wayfinder-mcp/tickets/G2-log16-v1-api.md): MemoryNode, write/query/equalize, status resource
- [G3 — Сценарии использования MCP-серверов агентом](plans/wayfinder-mcp/tickets/G3-usage-scenarios.md): как агент пишет/читает субстрат, изоляция проектов
- [G4 — Интеграция MCP-серверов с ai-agent](plans/wayfinder-mcp/tickets/G4-integration.md): конфигурация, запуск, регистрация инструментов, обработка ошибок

### Блокирующие зависимости

```
R1 ──→ G1 ──→ G3 ──→ G4
R2 ──→ G2 ──→ G3 ──→ G4
R3 ──→ G2 ──→ G3 ──→ G4
R3 ──→ G4
```

### Фронтир (первый тикет для работы)

Фронтир — это **R1, R2, R3** (исследования не имеют блокирующих зависимостей). Их можно запускать параллельно. После их завершения открывается фронтир **G1** и **G2**.

## Not yet specified

- **Стратегия тестирования**: моки, интеграционные тесты — будет определена после G4
- **LOG16 v2+**: SubstrateCompressor (NumPy), FractalKAN, персистентность (SQLite/Redis) — отложено после v1
- **План итераций v1/v2/v3**: будет составлен после закрытия всех G-тикетов

## Out of scope

- **LSP-сервер** — только Tree-sitter в v1, LSP в будущих итерациях
- **Web UI / дашборд** — серверы работают через MCP-протокол
- **Другие языки кроме Python** — v1 только Python, расширение языков в будущем
- **Изменения в core.py / core_tools.py** — ядро ai-agent immutable