# -*- coding: utf-8 -*-
# modules/llm/adapter.py — Адаптер для Ollama API
#
# Переход с /api/generate + ручной ChatML на /api/chat.
# Шаблон подставляет сам Ollama, разметка не привязана к Qwen.
#
# Usage:
#   from modules.llm import call_chat
#   response = call_chat("system prompt", "user prompt", model="qwen2.5-coder:7b")

import json
import time
from typing import Optional

import requests
from rich.console import Console

console = Console()

DEFAULT_OLLAMA_URL = "http://192.168.5.7:11434"
DEFAULT_MODEL = "qwen2.5-coder:14b"
DEFAULT_TIMEOUT = 120  # секунд на один запрос
MAX_RETRIES = 2
RETRY_DELAY = 2.0  # секунд между retry


class OllamaAdapter:
    """Адаптер для вызова Ollama через /api/chat."""

    def __init__(
        self,
        base_url: str = DEFAULT_OLLAMA_URL,
        default_model: str = DEFAULT_MODEL,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = MAX_RETRIES,
        retry_delay: float = RETRY_DELAY,
    ):
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def call_chat(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.2,
        num_ctx: int = 8192,
        stream: bool = False,
    ) -> str:
        """Вызов LLM через /api/chat.

        Ollama сам подставляет ChatML в зависимости от модели.
        Возвращает текст ответа или пустую строку при ошибке.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        payload = {
            "model": model or self.default_model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_ctx": num_ctx,
            },
        }

        last_error = None
        for attempt in range(1 + self.max_retries):
            try:
                response = requests.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("message", {}).get("content", "")

            except requests.Timeout:
                last_error = f"Timeout after {self.timeout}s"
                console.print(
                    f"[yellow]⏱ Ollama timeout (attempt {attempt + 1}): "
                    f"{last_error}[/yellow]"
                )
            except requests.ConnectionError as e:
                last_error = f"Connection refused: {e}"
                console.print(
                    f"[yellow]🔌 Ollama connection error (attempt {attempt + 1}): "
                    f"{last_error}[/yellow]"
                )
            except requests.HTTPError as e:
                # HTTP 4xx/5xx — не retry
                console.print(
                    f"[red]❌ Ollama HTTP error: {e}[/red]"
                )
                return ""
            except Exception as e:
                last_error = str(e)
                console.print(
                    f"[yellow]⚠️ Ollama error (attempt {attempt + 1}): "
                    f"{last_error}[/yellow]"
                )

            if attempt < self.max_retries:
                time.sleep(self.retry_delay * (attempt + 1))

        console.print(
            f"[red]❌ Ollama call failed after {self.max_retries + 1} attempts: "
            f"{last_error}[/red]"
        )
        return ""

    def call_generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        """Legacy вызов через /api/generate с ручным ChatML-шаблоном.

        Используется как fallback для моделей, которые не работают через
        /api/chat (единичные случаи). Постепенно удаляется.
        """
        prompt = (
            f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
            f"<|im_start|>user\n{user_prompt}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )

        payload = {
            "model": model or self.default_model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json().get("response", "")
        except Exception as e:
            console.print(
                f"[red]❌ Ollama generate error: {e}[/red]"
            )
            return ""


# ──────────────────────────────────────────────
# Удобный глобальный экземпляр и функции
# ──────────────────────────────────────────────

_default_adapter = OllamaAdapter()


def call_chat(
    system_prompt: str,
    user_prompt: str,
    model_override: Optional[str] = None,
    temperature: float = 0.2,
    num_ctx: int = 8192,
) -> str:
    """Вызов LLM через /api/chat (удобная обёртка)."""
    return _default_adapter.call_chat(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=model_override,
        temperature=temperature,
        num_ctx=num_ctx,
    )


def call_ollama_legacy(
    system_prompt: str,
    user_prompt: str,
    model_override: Optional[str] = None,
) -> str:
    """Старый вызов через /api/generate (обратная совместимость)."""
    return _default_adapter.call_generate(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=model_override,
    )