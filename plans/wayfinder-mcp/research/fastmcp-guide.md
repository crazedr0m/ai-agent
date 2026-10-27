# FastMCP SDK — Research Results

**Тикет**: [R3](../tickets/R3-fastmcp-research.md)
**Статус**: closed → resolved
**Дата**: 2026-10-27

## Установка и запуск

```bash
pip install fastmcp
# Версия: 4.1.4 (установлена)
```

## Объявление инструментов (@mcp.tool())

```python
from fastmcp import FastMCP

mcp = FastMCP("my-server", version="1.0.0")

@mcp.tool()
def my_tool(name: str, count: int = 1) -> str:
    """Описание инструмента (это docstring → MCP description)."""
    return f"Hello {name} × {count}"
```

Поддерживаемые типы аргументов:
- `str`, `int`, `float`, `bool`
- `list[str]`, `dict[str, Any]` из typing
- `Optional[str]`, `Optional[int]`
- Pydantic BaseModel (для сложных структур)

## Объявление ресурсов (@mcp.resource())

```python
@mcp.resource("substrate://status")
def get_status() -> str:
    """Описание ресурса."""
    return "Resource content"
```

Формат URI — произвольная схема, обычно `{server}://{path}`.
Ресурсы возвращают строку (text) или bytes (binary).

## Объявление промптов (@mcp.prompt())

```python
@mcp.prompt()
def my_prompt(context: str) -> list[Message]:
    """Описание промпта."""
    return [
        {"role": "system", "content": f"You know: {context}"},
        {"role": "user", "content": "Your task..."}
    ]
```

## Настройка транспорта

```python
# STDIO (по умолчанию)
mcp.run(transport="stdio")

# SSE
mcp.run(transport="sse", host="127.0.0.1", port=3300)
```

## run() и main()

`FastMCP.run()` — блокирующий вызов, который запускает сервер. Исползуется в `if __name__ == "__main__":`.

## Тестирование локально

**MCP Inspector**: `npx @modelcontextprotocol/inspector` — GUI для тестирования MCP-серверов.
Но для unit-тестов просто импортируем функции:

```python
from mcp_servers.<name>.tools import my_tool

def test_my_tool():
    result = my_tool("test", count=2)
    assert "Hello test × 2" in result
```

## Best practices

1. **Один подкаталог — один сервер** (single-responsibility) внутри `mcp_servers/`
2. **docstring → MCP description** — пишите осмысленные docstring
3. **Типизация** — используйте type hints, они автоматом конвертируются в JSON Schema
4. **Обработка ошибок** — возвращайте осмысленные строки, не крашитесь
5. **main() с argparse** — для поддержки `--transport` и `--port`
6. **Ресурсы для визуализации** — текстовые (Markdown/ASCII) для чтения LLM
7. **stdio — дефолт** — не требует открытых портов, работает из subprocess
8. **Тестируйте через импорт** — функции остаются обычным Python-кодом
9. **Modular-архитектура** — каждый сервер разбивается на `server.py`, `tools.py`, `helpers.py`
10. **Порядок импортов** — `mcp = FastMCP(...)` создаётся ДО импорта `tools.py` (см. server.py)

## Структура проекта (modular-архитектура)

```
mcp_servers/
├── __init__.py              # версия пакета
├── <server_name>/           # один подкаталог на сервер
│   ├── __init__.py          # точка входа: main() с argparse
│   ├── server.py            # FastMCP-инстанс + import tools
│   ├── tools.py             # @mcp.tool() инструменты
│   └── helpers.py           # вспомогательные функции (опционально)
```

### Детали modular-архитектуры

- **server.py** создаёт `mcp = FastMCP(...)` и импортирует `tools.py` для регистрации декораторов
- **tools.py** импортирует `mcp` из `server.py` (это безопасно — `mcp` уже создан на момент выполнения)
- **__init__.py** содержит `main()` с argparse и re-export инструментов для тестов
- Запуск: `python -m mcp_servers.<name>` вместо `python mcp_server_<name>.py`