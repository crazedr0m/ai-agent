# -*- coding: utf-8 -*-
# modules/settings.py — Единая конфигурация проекта
#
# Единственный источник правды для URL Ollama, имён моделей и путей.
# Значения читаются из окружения (.env через python-dotenv) с дефолтами.

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _env_str(key: str, default: str) -> str:
    value = os.environ.get(key)
    return value if value else default


def _env_int(key: str, default: int) -> int:
    raw = os.environ.get(key)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    ollama_base_url: str
    model_architect: str
    model_coder: str
    model_meta: str
    prompts_json: Path
    tasks_json: Path
    shared_context: Path
    checkpoints_dir: Path
    traces_dir: Path
    test_timeout: int
    max_concurrency: int


def load_settings() -> Settings:
    return Settings(
        ollama_base_url=_env_str("OLLAMA_BASE_URL", "http://192.168.5.7:11434"),
        model_architect=_env_str("ARCHITECT_MODEL", "qwen3-coder:30b"),
        model_coder=_env_str("CODER_MODEL", "qwen2.5-coder:14b"),
        model_meta=_env_str("META_MODEL", "deepseek-r1:32b"),
        prompts_json=PROJECT_ROOT / "prompts.json",
        tasks_json=PROJECT_ROOT / "tasks.json",
        shared_context=PROJECT_ROOT / "shared_context.json",
        checkpoints_dir=PROJECT_ROOT / "checkpoints",
        traces_dir=PROJECT_ROOT / _env_str("TRACES_DIR", "traces"),
        test_timeout=_env_int("TEST_TIMEOUT", 300),
        max_concurrency=_env_int("MAX_CONCURRENCY", 2),
    )


settings = load_settings()
