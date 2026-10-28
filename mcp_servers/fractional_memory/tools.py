# -*- coding: utf-8 -*-
# mcp_servers/fractional_memory/tools.py — Инструменты сервера дробно-слойной памяти
#
# 3 инструмента:
#   - write_fact         — запись факта
#   - query_facts        — поиск по gate_trigger
#   - consolidate_memory — пересчёт band + GC
#
# 1 ресурс:
#   - memory://bands — визуализация распределения

import json

from mcp_servers.fractional_memory.server import mcp
from mcp_servers.fractional_memory.helpers import (
    write,
    query,
    equalize,
    get_status,
)


@mcp.tool()
def write_fact(payload: str, gate_trigger: str = "") -> str:
    """Записать факт в память.

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
def query_facts(query_text: str, max_results: int = 50) -> str:
    """Найти факты в памяти по ключевым словам.

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
def consolidate_memory() -> str:
    """Пересчитать band для всех узлов + удалить decayed.

    Выполняет:
      1. Пересчёт frequency_band по дробно-логарифмической формуле для всех узлов
      2. Удаление узлов, упавших ниже Band 0
      3. Возврат отчёта с распределением по band

    Можно вызывать вручную или периодически из агента.
    """
    report = equalize()
    return json.dumps(report, indent=2, ensure_ascii=False)


@mcp.resource("memory://bands")
def memory_status() -> str:
    """Визуализация распределения узлов памяти по 16 band."""
    return get_status()
