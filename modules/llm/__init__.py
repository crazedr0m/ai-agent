# -*- coding: utf-8 -*-
# modules/llm/__init__.py — экспорт адаптера
#
# from modules.llm import OllamaAdapter, call_chat, call_ollama_legacy
# from modules.llm import get_model_profile, get_profile_value

from .adapter import (
    OllamaAdapter,
    call_chat,
    call_ollama_legacy,
    get_model_profile,
    get_profile_value,
)

__all__ = [
    "OllamaAdapter",
    "call_chat",
    "call_ollama_legacy",
    "get_model_profile",
    "get_profile_value",
]