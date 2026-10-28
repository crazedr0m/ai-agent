# -*- coding: utf-8 -*-
# modules/zones.py — Зоны мутабельности файлов проекта (ADR-001)
#
# Единственный источник правды о том, какой файл в какую зону входит.
# Используется инструментами записи (modules/dev_tools.py), hot reload
# (modules/hot_reload.py) и мета-оптимизатором промптов.
#
# Зоны:
#   kernel     — только человек, никаких правок агентом
#   supervised — агент может менять после подтверждения человеком (y/n)
#   autonomous — агент может менять самостоятельно
#   None       — файл вне проекта или не отнесён ни к одной зоне

import os
from typing import Optional

from modules.settings import PROJECT_ROOT

KERNEL_PATTERNS = (
    "venv/",
    ".git/",
)

SUPERVISED_PATTERNS = (
    "core/",
)

AUTONOMOUS_PATTERNS = (
    "core_tools.py",
    "agents/",
    "modules/",
    "prompts/",
    "prompts.json",
    "mcp_servers/",
    "mcp_server_",
)

ZONES = ("kernel", "supervised", "autonomous")


def relative_to_project(filepath: str) -> Optional[str]:
    """Привести путь к виду relative-to-PROJECT_ROOT.

    Возвращает None, если путь лежит вне корня проекта.
    """
    if not filepath:
        return None

    root = str(PROJECT_ROOT).replace("\\", "/")
    candidate = os.path.normpath(str(filepath).replace("\\", "/")).replace("\\", "/")

    if candidate == root:
        return ""

    if candidate.startswith("/"):
        if not candidate.startswith(root + "/"):
            return None
        candidate = candidate[len(root) + 1:]

    while candidate.startswith("./"):
        candidate = candidate[2:]

    candidate = candidate.lstrip("/")

    if candidate in ("", "."):
        return ""

    return candidate


def _matches(rel_path: str, patterns: tuple) -> bool:
    return any(rel_path == pattern or rel_path.startswith(pattern) for pattern in patterns)


def zone_of(filepath: str) -> Optional[str]:
    """Определить зону мутабельности файла.

    Возвращает 'kernel', 'supervised', 'autonomous' или None.
    """
    rel_path = relative_to_project(filepath)
    if not rel_path:
        return None

    if _matches(rel_path, KERNEL_PATTERNS):
        return "kernel"

    if _matches(rel_path, SUPERVISED_PATTERNS):
        return "supervised"

    if _matches(rel_path, AUTONOMOUS_PATTERNS):
        return "autonomous"

    return None


def is_writable_without_approval(filepath: str) -> bool:
    """True, если агент может менять файл без подтверждения человека."""
    return zone_of(filepath) == "autonomous"


def describe_zone(zone: Optional[str]) -> str:
    """Человекочитаемое описание зоны."""
    if zone == "kernel":
        return "kernel — только человек"
    if zone == "supervised":
        return "supervised — требуется подтверждение (y/n)"
    if zone == "autonomous":
        return "autonomous — агент может менять самостоятельно"
    return "вне зон ADR-001"