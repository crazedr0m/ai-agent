# -*- coding: utf-8 -*-
# mcp_server_fetch.py — MCP-сервер для веб-запросов
#
# Фаза 3.3: Web fetch MCP-сервер на FastMCP.
# Предоставляет инструменты: fetch_url, fetch_markdown.
#
# Запуск:
#     python -m mcp_server_fetch  # stdio (по умолчанию)
#     python mcp_server_fetch.py --transport sse --port 3200

import argparse
import json
from typing import Optional

from fastmcp import FastMCP

mcp = FastMCP(
    "fetch-server",
    instructions="Web fetch: download URLs, convert HTML to markdown",
    version="1.0.0",
)


@mcp.tool()
def fetch_url(url: str, timeout: int = 30) -> str:
    """Загрузить содержимое URL.

    Args:
        url: полный URL для загрузки (включая http:// или https://)
        timeout: таймаут в секундах (по умолчанию 30)
    """
    import urllib.request
    import urllib.error

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "MCP-Fetch/1.0 (ai-agent)",
                "Accept": "text/html,application/json,text/plain,*/*",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read()
            # Пробуем декодировать как UTF-8
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                text = content.decode("utf-8", errors="replace")

            info = [
                f"URL: {url}",
                f"Status: {resp.status}",
                f"Content-Type: {resp.headers.get('Content-Type', 'unknown')}",
                f"Size: {len(content)} B",
                "",
                text[:50000],  # лимит 50KB
            ]
            if len(text) > 50000:
                info.append(f"\n... (вывод обрезан, всего {len(text)} B)")
            return "\n".join(info)

    except urllib.error.HTTPError as e:
        return f"HTTP Error {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return f"URL Error: {e.reason}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def fetch_markdown(url: str, timeout: int = 30) -> str:
    """Загрузить URL и конвертировать HTML в Markdown.

    Args:
        url: полный URL для загрузки
        timeout: таймаут в секундах (по умолчанию 30)
    """
    import urllib.request
    import urllib.error
    import html.parser

    class _HTMLStripper(html.parser.HTMLParser):
        """Простой HTML-to-text конвертер."""

        def __init__(self):
            super().__init__()
            self._text = []
            self._skip = False

        def handle_starttag(self, tag, attrs):
            if tag in ("script", "style"):
                self._skip = True
            if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                self._text.append("\n## ")
            elif tag == "p":
                self._text.append("\n\n")
            elif tag == "br":
                self._text.append("\n")
            elif tag == "li":
                self._text.append("\n- ")
            elif tag in ("hr", "tr"):
                self._text.append("\n---\n")

        def handle_endtag(self, tag):
            if tag in ("script", "style"):
                self._skip = False

        def handle_data(self, data):
            if not self._skip:
                self._text.append(data)

        def get_text(self):
            return "".join(self._text)

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "MCP-Fetch/1.0 (ai-agent)",
                "Accept": "text/html,text/plain,*/*",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read()
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                text = content.decode("utf-8", errors="replace")

            stripper = _HTMLStripper()
            try:
                stripper.feed(text)
                markdown = stripper.get_text().strip()
            except Exception:
                markdown = text[:50000]

            info = [
                f"URL: {url}",
                f"Status: {resp.status}",
                f"Size: {len(content)} B",
                "",
                markdown[:50000],
            ]
            if len(markdown) > 50000:
                info.append(f"\n... (вывод обрезан, всего {len(markdown)} B)")
            return "\n".join(info)

    except urllib.error.HTTPError as e:
        return f"HTTP Error {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return f"URL Error: {e.reason}"
    except Exception as e:
        return f"Error: {e}"


def main():
    parser = argparse.ArgumentParser(description="Web Fetch MCP Server")
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio")
    parser.add_argument("--port", type=int, default=3200)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    if args.transport == "sse":
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()