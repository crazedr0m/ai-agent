# -*- coding: utf-8 -*-
# modules/llm/adapter.py — Адаптер для Ollama API
#
# Переход с /api/generate + ручной ChatML на /api/chat.
# Шаблон подставляет сам Ollama, разметка не привязана к Qwen.
#
# Фаза 1.6: Профили моделей — параметры (таймаут, температура, num_ctx)
# настраиваются через model_profiles.json.
#
# Usage:
#   from modules.llm import call_chat
#   response = call_chat("system prompt", "user prompt", model="qwen2.5-coder:7b")

import json
import os
import time
from typing import Optional

import requests
from rich.console import Console

from modules.settings import settings

console = Console()

DEFAULT_OLLAMA_URL = settings.ollama_base_url
DEFAULT_MODEL = settings.model_coder
DEFAULT_TIMEOUT = 120  # секунд на один запрос
MAX_RETRIES = 2
RETRY_DELAY = 2.0  # секунд между retry

# ──────────────────────────────────────────────
# Загрузка профилей моделей (Фаза 1.6)
# ──────────────────────────────────────────────

_PROFILES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "model_profiles.json",
)

_PROFILES_CACHE = None  # type: Optional[dict]


def _load_profiles() -> dict:
    """Загрузить model_profiles.json, кешировать."""
    global _PROFILES_CACHE
    if _PROFILES_CACHE is not None:
        return _PROFILES_CACHE

    try:
        with open(_PROFILES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        _PROFILES_CACHE = data
        return data
    except (FileNotFoundError, json.JSONDecodeError) as e:
        console.print(f"[dim]⚠️ model_profiles.json не загружен: {e}[/dim]")
        _PROFILES_CACHE = {"profiles": {}, "defaults": {}}
        return _PROFILES_CACHE


def get_model_profile(model_name: str) -> dict:
    """Получить профиль модели. Неизвестные поля заполняются из defaults."""
    data = _load_profiles()
    defaults = data.get("defaults", {})
    profile = data.get("profiles", {}).get(model_name, {})
    merged = dict(defaults)
    merged.update(profile)
    return merged


def get_profile_value(model_name: str, key: str, default=None):
    """Получить одно значение из профиля модели."""
    return get_model_profile(model_name).get(key, default)


# ──────────────────────────────────────────────
# Адаптер
# ──────────────────────────────────────────────


class OllamaAdapter:
    """Адаптер для вызова Ollama через /api/chat.

    Поддерживает профили моделей из model_profiles.json (Фаза 1.6):
    - timeout, max_retries, temperature, num_ctx переопределяются из профиля
    - Если профиля нет — используются значения по умолчанию
    """

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

    def _resolve_params(self, model: Optional[str] = None,
                        temperature: Optional[float] = None,
                        num_ctx: Optional[int] = None,
                        timeout: Optional[int] = None,
                        max_retries: Optional[int] = None) -> dict:
        """Объединить явные параметры с профилем модели.

        Явные параметры имеют приоритет над профилем.
        """
        model_name = model or self.default_model
        profile = get_model_profile(model_name)

        return {
            "model": model_name,
            "temperature": temperature if temperature is not None else profile.get("temperature", 0.2),
            "num_ctx": num_ctx if num_ctx is not None else profile.get("num_ctx", 8192),
            "timeout": timeout if timeout is not None else profile.get("timeout", self.timeout),
            "max_retries": max_retries if max_retries is not None else profile.get("max_retries", self.max_retries),
        }

    def call_chat(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        num_ctx: Optional[int] = None,
        stream: bool = False,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
    ) -> str:
        """Вызов LLM через /api/chat.

        Ollama сам подставляет ChatML в зависимости от модели.
        Параметры берутся из model_profiles.json, если не указаны явно.
        Возвращает текст ответа или пустую строку при ошибке.
        """
        params = self._resolve_params(
            model=model, temperature=temperature,
            num_ctx=num_ctx, timeout=timeout, max_retries=max_retries,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        payload = {
            "model": params["model"],
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": params["temperature"],
                "num_ctx": params["num_ctx"],
            },
        }

        effective_timeout = params["timeout"]
        effective_retries = params["max_retries"]

        last_error = None
        for attempt in range(1 + effective_retries):
            try:
                response = requests.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=effective_timeout,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("message", {}).get("content", "")

            except requests.Timeout:
                last_error = f"Timeout after {effective_timeout}s"
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

            if attempt < effective_retries:
                time.sleep(self.retry_delay * (attempt + 1))

        console.print(
            f"[red]❌ Ollama call failed after {effective_retries + 1} attempts: "
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