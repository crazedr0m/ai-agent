import re

def extract_code_from_markdown(text: str) -> str:
    """Извлекает код независимо от регистра символов в тегах."""
    match = re.search(r"```python\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""