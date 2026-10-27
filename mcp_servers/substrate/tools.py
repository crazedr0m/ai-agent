# -*- coding: utf-8 -*-
# mcp_servers/substrate/tools.py — Инструменты LOG16 Substrate MCP-сервера
#
# 3 инструмента:
#   - write_to_substrate — запись факта
#   - query_substrate    — поиск по gate_trigger
#   - equalize_memory    — пересчёт band + GC
#
# 1 ресурс:
#   - substrate://status — визуализация распределения

import json

from mcp_servers.substrate.server import mcp
from mcp_servers.substrate.helpers import (
    write,
    query,
    equalize,
    get_status,
)


@mcp.tool()
def write_to_substrate(payload: str, gate_trigger: str = "") -> str:
    """Записать факт в субстрат (LOG16-память).

    Создаёт MemoryNode в Band 0 (Spike/HF).
    Если аналогичный gate_trigger уже существует — увеличивает
    access_count и пересчитывает band.

    Args:
        payload: содержание факта (сжатый текст)
        gate_trigger: ключевые слова для активации (через пробел)
    """
    node_id = write(payload, gate_trigger)
    return json.dumps({
        "status": "written",
        "node_id": node_id,
    }, indent=2, ensure_ascii=False)


@mcp.tool()
def query_substrate(query_text: str, max_results: int = 50) -> str:
    """Найти факты в субстрате по ключевым словам.

    Стратегия поиска:
      - Band 15 (Core) — всегда возвращается
      - Bands 1-14 — только при совпадении gate_trigger
      - Band 0 — топ-3 последних spike
      - Результаты сортируются по band (убывание)

    Args:
        query_text: строка поиска (сравнивается с gate_trigger)
        max_results: макс. количество результатов (по умолч. 50)
    """
    results = query(query_text, max_results=max_results)

    if not results:
        return json.dumps({
            "status": "no_results",
            "query": query_text,
            "nodes": [],
        }, indent=2, ensure_ascii=False)

    return json.dumps({
        "status": "found",
        "query": query_text,
        "count": len(results),
        "nodes": results,
    }, indent=2, ensure_ascii=False, default=str)


@mcp.tool()
def equalize_memory() -> str:
    """Пересчитать band для всех узлов + удалить decayed.

    Выполняет:
      1. Пересчёт frequency_band по формуле log16 для всех узлов
      2. Удаление узлов, упавших ниже Band 0
      3. Возврат отчёта с распределением по band

    Можно вызывать вручную или периодически из агента.
    """
    report = equalize()
    return json.dumps(report, indent=2, ensure_ascii=False)


@mcp.resource("substrate://status")
def substrate_status() -> str:
    """Визуализация распределения узлов LOG16 по 16 band."""
    return get_status()