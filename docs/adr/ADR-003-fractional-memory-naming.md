# ADR-003: Вынос брендов LOG16/Substrate из кода в пользу принципных имён

## Статус

Принят (28.10.2026)

## Контекст

MCP-сервер долговременной памяти и его интеграция в конвейер миграции были названы
терминами первоисточника концепции — **LOG16** и **Substrate** (канал
[Техножнец](https://t.me/technojnec)). Термины проникли в имена каталогов
(`mcp_servers/substrate/`), модулей (`modules/log16_integration.py`), классов
(`LOG16Integration`), инструментов (`write_to_substrate`, `query_substrate`,
`equalize_memory`), ресурса (`substrate://status`), ключ конфига (`"substrate"`)
и префикс MCP-инструментов (`substrate__`).

Проблема: имена-бренды завязаны на внешний источник и не описывают **принцип**
работы. Читатель кода не понимает, что делает модуль, не зная истории концепции.
Кроме того, атрибуция чужого авторства должна оставаться в документах, а не в
исполняемом коде.

### Рассмотренные варианты

**Вариант A: оставить имена как есть**
- Привычно для тех, кто следит за первоисточником.
- Код остаётся непонятным без внешнего контекста; бренд «протекает» в API.

**Вариант B: нейтральные описательные имена по принципу**
- **LOG16** → **Fractional Cache** — дробно-логарифмическая шкала полос.
- **Substrate** → **Fractional Layered Memory** — слоистое хранилище фактов по полосам.
- Атрибуция первоисточника остаётся только в документах.

## Решение

**Выбран Вариант B.** Бренды вынесены из кода; в документах
([`docs/log16.md`](../log16.md), [`docs/AR2-log16.md`](../AR2-log16.md),
[`docs/target.txt`](../target.txt), [`plans/wayfinder-mcp/`](../../plans/wayfinder-mcp/map.md))
ссылки на первоисточник сохранены без изменений.

### Карта переименований

| Область | Старое | Новое |
|---|---|---|
| Каталог сервера | `mcp_servers/substrate/` | `mcp_servers/fractional_memory/` |
| Имя FastMCP | `substrate` | `fractional_memory` |
| Префикс MCP-инструментов | `substrate__` | `fractional_memory__` |
| Запись факта | `write_to_substrate` | `write_fact` |
| Поиск фактов | `query_substrate` | `query_facts` |
| Пересчёт + GC | `equalize_memory` | `consolidate_memory` |
| MCP-ресурс | `substrate://status` | `memory://bands` |
| Мат-функция | `_log16()` | `_fractional_band()` |
| Класс интеграции | `LOG16Integration` | `FractionalMemory` |
| Модуль интеграции | `modules/log16_integration.py` | `modules/fractional_memory.py` |
| Ключ конфига | `substrate` | `fractional_memory` |
| Тест | `tests/test_mcp_substrate.py` | `tests/test_mcp_fractional_memory.py` |
| Атрибут/параметр | `self.log16`, `log16=` | `self.memory`, `memory=` |

### Что осталось неизменным

- `MemoryNode`, `frequency_band`, `gate_trigger` — нейтральны изначально.
- Формула `band = floor(log_16(age + 1) - log_16(access_count + 1))` — математика та же.
- Документы-первоисточники и исследования wayfinder — атрибуция сохранена.

## Последствия

- Код самодокументируем: имена описывают слои и дробную шкалу, а не автора концепции.
- Публичный API MCP-сервера изменился — внешние потребители должны использовать
  `fractional_memory__write_fact` / `fractional_memory__query_facts` /
  `fractional_memory__consolidate_memory`.
- Конфиг [`mcp_servers.json`](../../mcp_servers.json) и префиксы реестра инструментов
  обновлены согласованно.
