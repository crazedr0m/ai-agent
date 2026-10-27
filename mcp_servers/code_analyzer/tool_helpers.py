# -*- coding: utf-8 -*-
# mcp_servers/code_analyzer/tool_helpers.py — Общие хелперы для инструментов

from mcp_servers.code_analyzer.languages import (
    get_analyzer,
    get_supported_languages,
    infer_language,
)


def _resolve_analyzer(file_path: str, language: str | None = None) -> tuple:
    """Определить анализатор по языку или расширению файла.

    Returns:
        (BaseAnalyzer | None, str | None) — (анализатор, сообщение об ошибке)
    """
    if language is None:
        language = infer_language(file_path)
        if language is None:
            return None, f"Не удалось определить язык для '{file_path}'"

    analyzer = get_analyzer(language)
    if analyzer is None:
        supported = ", ".join(get_supported_languages())
        return None, f"Язык '{language}' не поддерживается. Поддерживаются: {supported}"

    return analyzer, None