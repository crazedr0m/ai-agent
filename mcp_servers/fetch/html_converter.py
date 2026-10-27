# -*- coding: utf-8 -*-
# mcp_servers/fetch/html_converter.py — Конвертер HTML в упрощённый Markdown

import html.parser


class HTMLStripper(html.parser.HTMLParser):
    """Простой HTML-to-text конвертер с базовой разметкой.

    Преобразует HTML-теги в упрощённую Markdown-разметку:
    - Заголовки (h1-h6) → "## "
    - Абзацы → двойной перенос строки
    - Списки (li) → "- "
    - Разделители (hr) → "---"
    - script/style → пропускаются
    """

    def __init__(self):
        super().__init__()
        self._text: list[str] = []
        self._skip: bool = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
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

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style"):
            self._skip = False

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self._text.append(data)

    def get_text(self) -> str:
        """Вернуть накопленный текст."""
        return "".join(self._text)