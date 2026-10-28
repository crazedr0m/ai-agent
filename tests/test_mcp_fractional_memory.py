# -*- coding: utf-8 -*-
# tests/test_mcp_fractional_memory.py — Контрактные тесты для сервера дробно-слойной памяти

import unittest
import json
import time

from tests import *  # noqa: sys.path
from mcp_servers.fractional_memory.helpers import reset_store


class TestMCPServerFractionalMemory(unittest.TestCase):
    """Контрактные тесты для сервера дробно-слойной памяти (Фаза 5.3)."""

    def setUp(self):
        reset_store()

    def test_write_fact(self):
        """write_fact создаёт узел в Band 0."""
        from mcp_servers.fractional_memory.tools import write_fact
        result = write_fact("fact: Python 3.12 released", "python release")
        data = json.loads(result)
        self.assertEqual(data["status"], "written")
        self.assertIn("node_id", data)

    def test_write_and_query(self):
        """Записанный факт находится через query."""
        from mcp_servers.fractional_memory.tools import write_fact, query_facts
        write_fact("fact: Python 3.12 released", "python release")
        result = query_facts("python")
        data = json.loads(result)
        self.assertEqual(data["status"], "found")
        self.assertGreaterEqual(data["count"], 1)

    def test_query_no_results(self):
        """query возвращает пустой результат для несуществующего ключа."""
        from mcp_servers.fractional_memory.tools import query_facts
        result = query_facts("zzz_nonexistent_zzz")
        data = json.loads(result)
        self.assertEqual(data["status"], "no_results")

    def test_write_duplicate_trigger(self):
        """Повторная запись с тем же gate_trigger увеличивает access_count."""
        from mcp_servers.fractional_memory.tools import write_fact
        from mcp_servers.fractional_memory.helpers import _default_store

        nid1 = json.loads(write_fact("fact one", "trigger1"))["node_id"]
        nid2 = json.loads(write_fact("fact two", "trigger1"))["node_id"]

        # Должен быть тот же ID (обновлён, не создан заново)
        self.assertEqual(nid1, nid2)
        self.assertEqual(_default_store[nid1].access_count, 2)

    def test_consolidate_memory(self):
        """consolidate_memory возвращает отчёт с распределением по band."""
        from mcp_servers.fractional_memory.tools import write_fact, consolidate_memory

        write_fact("fact A", "alpha")
        write_fact("fact B", "beta")
        write_fact("fact C", "gamma")

        result = consolidate_memory()
        data = json.loads(result)
        self.assertIn("total_nodes", data)
        self.assertIn("distribution", data)
        self.assertGreaterEqual(data["total_nodes"], 3)

    def test_memory_status_resource(self):
        """memory://bands возвращает ASCII-диаграмму."""
        from mcp_servers.fractional_memory.tools import memory_status
        result = memory_status()
        self.assertIn("Fractional Memory Status", result)
        self.assertIn("Band", result)
        self.assertIn("Total nodes", result)

    def test_band_calculation(self):
        """MemoryNode.recalculate_band правильно вычисляет полосу."""
        from mcp_servers.fractional_memory.helpers import MemoryNode
        import time

        # Новый узел с age=0, access_count=1 → band=0
        node = MemoryNode(
            node_id="test1",
            payload="test",
            gate_trigger="test",
            frequency_band=0,
            access_count=1,
            last_accessed=time.time(),
        )
        band = node.recalculate_band()
        self.assertEqual(band, 0)

        # Старый узел (age большой) с access_count=0 → band растёт
        # log_16(3651) - log_16(1) ≈ 2.96 → floor = 2
        old_node = MemoryNode(
            node_id="test2",
            payload="old",
            gate_trigger="old",
            frequency_band=0,
            access_count=0,
            last_accessed=time.time() - 86400 * 365 * 10,  # 10 лет назад
        )
        old_band = old_node.recalculate_band()
        self.assertEqual(old_band, 2)

    def test_query_band_filtering(self):
        """query корректно фильтрует по band."""
        from mcp_servers.fractional_memory.tools import write_fact, query_facts
        from mcp_servers.fractional_memory.helpers import _default_store

        nid = json.loads(write_fact("core fact", "core_rule"))["node_id"]
        # Вручную устанавливаем band=15 (Core)
        _default_store[nid].frequency_band = 15

        # Core факт должен находиться даже без совпадения gate_trigger
        result = query_facts("something_else")
        data = json.loads(result)
        self.assertGreaterEqual(data["count"], 1)


if __name__ == "__main__":
    unittest.main()
