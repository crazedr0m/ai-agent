# -*- coding: utf-8 -*-
# modules/eval/utils.py — Утилиты для eval-харнесса

from modules.settings import settings


def get_available_models() -> list[str]:
    """Получить список доступных моделей из Ollama."""
    import requests
    try:
        resp = requests.get(f"{settings.ollama_base_url}/api/tags", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        return [m["name"] for m in data.get("models", [])]
    except Exception as e:
        print(f"[yellow]⚠️ Не удалось получить список моделей: {e}[/yellow]")
        return []