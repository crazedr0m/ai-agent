# -*- coding: utf-8 -*-
# mcp_servers/fetch/tools.py — Инструменты fetch-сервера
#
# 2 инструмента:
#   - fetch_url       — загрузка содержимого URL
#   - fetch_markdown  — загрузка URL + конвертация HTML в Markdown

import urllib.request
import urllib.error

from mcp_servers.fetch.server import mcp
from mcp_servers.fetch.html_converter import HTMLStripper

# Лимит на размер вывода (50 KB)
_MAX_OUTPUT_SIZE = 50000


def _build_request(url: str, accept: str) -> urllib.request.Request:
    """Создать HTTP-запрос с user-agent."""
    return urllib.request.Request(
        url,
        headers={
            "User-Agent": "MCP-Fetch/1.0 (ai-agent)",
            "Accept": accept,
        },
    )


def _decode_content(content: bytes) -> str:
    """Декодировать контент как UTF-8 с fallback."""
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("utf-8", errors="replace")


def _truncate_output(text: str, url: str, status: int, content_type: str,
                     total_size: int) -> str:
    """Обрезать вывод до _MAX_OUTPUT_SIZE с информацией о статистике."""
    info = [
        f"URL: {url}",
        f"Status: {status}",
        f"Content-Type: {content_type}",
        f"Size: {total_size} B",
        "",
        text[:_MAX_OUTPUT_SIZE],
    ]
    if len(text) > _MAX_OUTPUT_SIZE:
        info.append(f"\n... (вывод обрезан, всего {total_size} B)")
    return "\n".join(info)


@mcp.tool()
def fetch_url(url: str, timeout: int = 30) -> str:
    """Загрузить содержимое URL.

    Args:
        url: полный URL для загрузки (включая http:// или https://)
        timeout: таймаут в секундах (по умолчанию 30)
    """
    try:
        req = _build_request(url, "text/html,application/json,text/plain,*/*")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read()
            text = _decode_content(content)
            return _truncate_output(
                text, url, resp.status,
                resp.headers.get("Content-Type", "unknown"),
                len(content),
            )
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
    try:
        req = _build_request(url, "text/html,text/plain,*/*")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read()
            text = _decode_content(content)

            stripper = HTMLStripper()
            try:
                stripper.feed(text)
                markdown = stripper.get_text().strip()
            except Exception:
                markdown = text[:_MAX_OUTPUT_SIZE]

            info = [
                f"URL: {url}",
                f"Status: {resp.status}",
                f"Size: {len(content)} B",
                "",
                markdown[:_MAX_OUTPUT_SIZE],
            ]
            if len(markdown) > _MAX_OUTPUT_SIZE:
                info.append(
                    f"\n... (вывод обрезан, всего {len(markdown)} B)"
                )
            return "\n".join(info)
    except urllib.error.HTTPError as e:
        return f"HTTP Error {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return f"URL Error: {e.reason}"
    except Exception as e:
        return f"Error: {e}"