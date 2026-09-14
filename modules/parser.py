# modules/parser.py
# Этот модуль агент МОЖЕТ модифицировать и улучшать автономно.

import re

def extract_code_from_markdown(text: str) -> str:
    """
    Извлекает чистый код из markdown-блоков.
    Если блоков нет, возвращает текст целиком.
    """
    # Базовый поиск блоков ```python ... ```
    code_blocks = re.findall(r"```(?:python)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if code_blocks:
        return code_blocks[0].strip()
    return text.strip()
