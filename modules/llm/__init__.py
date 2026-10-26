# -*- coding: utf-8 -*-
# modules/llm/__init__.py — экспорт адаптера
#
# from modules.llm import OllamaAdapter, call_chat, call_ollama_legacy

from .adapter import OllamaAdapter, call_chat, call_ollama_legacy

__all__ = ["OllamaAdapter", "call_chat", "call_ollama_legacy"]