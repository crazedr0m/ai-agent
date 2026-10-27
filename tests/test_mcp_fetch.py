# -*- coding: utf-8 -*-
# tests/test_mcp_fetch.py — Контрактные тесты для Web Fetch MCP-сервера

import unittest

from tests import *  # noqa: sys.path


class TestMCPServerFetch(unittest.TestCase):
    """Контрактные тесты для Web Fetch MCP-сервера (Фаза 3.4)."""

    def test_fetch_url_invalid(self):
        """fetch_url возвращает ошибку для невалидного URL."""
        from mcp_servers.fetch.tools import fetch_url
        result = fetch_url("http://localhost:1")
        self.assertTrue(
            "Error" in result or "ошибка" in result.lower() or "refused" in result.lower()
        )

    def test_fetch_markdown_invalid(self):
        """fetch_markdown возвращает ошибку для невалидного URL."""
        from mcp_servers.fetch.tools import fetch_markdown
        result = fetch_markdown("http://localhost:1")
        self.assertTrue(
            "Error" in result or "ошибка" in result.lower() or "refused" in result.lower()
        )


if __name__ == "__main__":
    unittest.main()