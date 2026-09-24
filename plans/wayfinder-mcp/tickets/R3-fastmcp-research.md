# [R3] Исследование FastMCP SDK

**Тип**: research  
**Статус**: open  
**Метка**: wayfinder:research  

## Question

Исследовать FastMCP (https://github.com/jlowin/fastmcp) и MCP Python SDK:

1. Как установить и запустить FastMCP?
2. Как объявить инструмент (`@mcp.tool()`)? Какие типы аргументов поддерживаются?
3. Как объявить ресурс (`@mcp.resource()`)? Какой формат URI?
4. Как объявить промпт (`@mcp.prompt()`)?
5. Как настроить транспорт (SSE, stdio)?
6. Как запустить сервер: `mcp.run()`?
7. Как тестировать MCP-сервер локально (MCP Inspector)?
8. Есть ли примеры production-ready MCP-серверов на Python?
9. Какие best practices по структуре проекта?

## Зависимости

Нет — это независимое исследование.

## Результат

Документ `plans/wayfinder-mcp/research/fastmcp-guide.md` с примерами кода и рекомендациями.