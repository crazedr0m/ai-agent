# -*- coding: utf-8 -*-
# mcp_servers/fractional_memory/helpers.py — Дробно-логарифмический движок: MemoryNode, equalize, query
#
# Реализует слоистую память с дробно-логарифмическими полосами:
#   - MemoryNode с полями id, payload, gate_trigger, frequency_band,
#     access_count, last_accessed, metadata
#   - recalculate_band() по дробно-логарифмической формуле
#   - write, query, equalize
#   - status resource (распределение по 16 band)

import math
import time
import copy
from typing import Optional

# ── Дробно-логарифмическая шкала полос ────────────────────────────


def _fractional_band(x: float) -> float:
    """Дробный логарифм по основанию 16 (шкала полос)."""
    return math.log(x) / math.log(16)


# ── MemoryNode ────────────────────────────────────────────────────


class MemoryNode:
    """Один факт в памяти.

    Поля:
        id: str — уникальный идентификатор
        payload: str — сжатый факт (содержание)
        gate_trigger: str — ключевые слова для активации
        frequency_band: int — номер полосы 0..15
        access_count: int — сколько раз был прочитан
        last_accessed: float — timestamp последнего доступа
        metadata: dict — дополнительные поля
    """

    def __init__(
        self,
        node_id: str,
        payload: str,
        gate_trigger: str = "",
        frequency_band: int = 0,
        access_count: int = 0,
        last_accessed: Optional[float] = None,
        metadata: Optional[dict] = None,
    ):
        self.id = node_id
        self.payload = payload
        self.gate_trigger = gate_trigger
        self.frequency_band = frequency_band
        self.access_count = access_count
        self.last_accessed = last_accessed or time.time()
        self.metadata = metadata or {}

    def recalculate_band(self) -> int:
        """Пересчитать полосу по дробно-логарифмической формуле.

        band = floor(log_16(age + 1) - log_16(access_count + 1))

        - age = время с последнего доступа (в условных единицах)
        - access_count = сколько раз читали
        """
        age_seconds = time.time() - self.last_accessed
        # Нормализуем age: 1 день = 1 единица
        age_days = max(0, age_seconds / 86400.0)

        raw = _fractional_band(age_days + 1) - _fractional_band(self.access_count + 1)
        band = max(0, min(15, int(raw)))
        self.frequency_band = band
        return band

    def access(self):
        """Зафиксировать обращение к узлу."""
        self.access_count += 1
        self.last_accessed = time.time()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "payload": self.payload,
            "gate_trigger": self.gate_trigger,
            "frequency_band": self.frequency_band,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MemoryNode":
        return cls(
            node_id=data["id"],
            payload=data["payload"],
            gate_trigger=data.get("gate_trigger", ""),
            frequency_band=data.get("frequency_band", 0),
            access_count=data.get("access_count", 0),
            last_accessed=data.get("last_accessed", time.time()),
            metadata=data.get("metadata", {}),
        )


# ── Хранилище полос памяти ────────────────────────────────────────


_default_store: dict[str, MemoryNode] = {}
_next_id: int = 0


def _generate_id() -> str:
    """Сгенерировать уникальный ID узла."""
    global _next_id
    _next_id += 1
    return f"node_{int(time.time())}_{_next_id}"


def write(payload: str, gate_trigger: str = "", metadata: Optional[dict] = None) -> str:
    """Записать факт в память.

    - Если похожий gate_trigger уже есть — увеличиваем access_count,
      пересчитываем band.
    - Иначе — создаём новый MemoryNode в Band 0 (Spike/HF).

    Returns:
        node_id созданного/обновлённого узла
    """
    # Ищем узел с таким же gate_trigger
    for node in _default_store.values():
        if node.gate_trigger == gate_trigger and gate_trigger:
            node.access()
            node.recalculate_band()
            return node.id

    node_id = _generate_id()
    node = MemoryNode(
        node_id=node_id,
        payload=payload,
        gate_trigger=gate_trigger,
        frequency_band=0,
        access_count=1,
        metadata=metadata or {},
    )
    _default_store[node_id] = node
    return node_id


def query(query_text: str, max_results: int = 50) -> list[dict]:
    """Поиск фактов по gate_trigger (keyword match).

    Стратегия:
      - Band 15 (Core) — всегда возвращается
      - Bands 1-14 — только при совпадении gate_trigger
      - Band 0 — топ-3 последних spike (по last_accessed)
      - Результаты сортируются по band (убывание)

    Args:
        query_text: строка поиска (сравнивается с gate_trigger)
        max_results: макс. количество результатов

    Returns:
        список MemoryNode.to_dict(), отсортированный по band
    """
    keywords = query_text.lower().split()
    results = []

    for node in _default_store.values():
        node.access()
        node.recalculate_band()
        band = node.frequency_band

        include = False
        if band == 15:
            include = True  # Core всегда
        elif band >= 1:
            # Проверяем совпадение gate_trigger с ключевыми словами
            trigger_lower = node.gate_trigger.lower()
            if any(kw in trigger_lower for kw in keywords) or not keywords:
                include = True
        elif band == 0:
            # Band 0 — только топ-3 позже
            include = True

        if include:
            results.append(node.to_dict())

    # Band 0: только топ-3 по last_accessed
    band0 = sorted(
        [r for r in results if r["frequency_band"] == 0],
        key=lambda x: x["last_accessed"],
        reverse=True,
    )[:3]

    # Bands 1-15: все
    bands_rest = sorted(
        [r for r in results if r["frequency_band"] > 0],
        key=lambda x: x["frequency_band"],
        reverse=True,
    )

    combined = band0 + bands_rest
    return combined[:max_results]


def equalize() -> dict:
    """Пересчитать band для всех узлов + удалить decayed (Band < 0).

    Returns:
        отчёт: сколько узлов обновлено, сколько удалено
    """
    updated = 0
    removed = 0
    to_delete = []

    for node_id, node in _default_store.items():
        old_band = node.frequency_band
        new_band = node.recalculate_band()
        if new_band != old_band:
            updated += 1
        if new_band < 0:
            to_delete.append(node_id)

    for node_id in to_delete:
        del _default_store[node_id]
        removed += 1

    return {
        "total_nodes": len(_default_store),
        "updated_bands": updated,
        "removed_decayed": removed,
        "distribution": _band_distribution(),
    }


def get_status() -> str:
    """Сформировать status resource: ASCII-диаграмма распределения по 16 band."""
    dist = _band_distribution()
    lines = ["## Fractional Memory Status", "", "### Distribution across 16 bands", ""]

    max_count = max(dist.values()) if any(dist.values()) else 1
    for band in range(15, -1, -1):
        count = dist.get(band, 0)
        bar_len = int((count / max_count) * 30) if max_count > 0 else 0
        bar = "█" * bar_len
        label = "CORE" if band == 15 else "SPIKE" if band == 0 else ""
        lines.append(f"  Band {band:2d} [{label:5s}] {bar} {count}")

    lines.append(f"\nTotal nodes: {sum(dist.values())}")
    return "\n".join(lines)


def _band_distribution() -> dict[int, int]:
    """Распределение узлов по 16 band."""
    dist = {i: 0 for i in range(16)}
    for node in _default_store.values():
        band = node.frequency_band
        dist[band] = dist.get(band, 0) + 1
    return dist


def reset_store():
    """Сбросить хранилище (для тестов)."""
    _default_store.clear()
    global _next_id
    _next_id = 0
