# -*- coding: utf-8 -*-
# modules/hot_reload.py — Hot reload модулей изменяемой зоны (Фаза 4.6)
#
# Замена `os.execv` (перезапуск всего процесса) на точечную перезагрузку
# модулей из autonomous/supervised зоны.
#
# Использование:
#     from modules.hot_reload import reload_module, reload_zone
#     reload_module("modules.tool_parser")  # перезагрузить один модуль
#     reload_zone("autonomous")             # перезагрузить все autonomous-модули

import importlib
import logging
import os
import sys
from typing import Optional

# Зоны мутабельности и соответствующие им пакеты
ZONE_MODULES: dict[str, list[str]] = {
    "autonomous": [
        "core_tools",
        "agents.casual_agent",
        "agents.migration_agent",
        "agents.retry_system",
        "modules.parser",
        "modules.tool_parser",
        "modules.tracer",
        "modules.mcp_client",
        "modules.eval_harness",
        "modules.sandbox",
        "modules.gate",
        "modules.retrospective",
        "modules.scaffold",
        "modules.hot_reload",
        "modules.llm",
        "modules.llm.adapter",
        "modules.dev_tools",
    ],
    "supervised": [
        "_core",
        "core",
        "core.core",
        "core.core_tools",
        "core.__init__",
    ],
    "kernel": [],  # не перегружается
}


def reload_module(module_name: str) -> bool:
    """Перезагрузить один модуль по имени.

    Args:
        module_name: полное имя модуля (например 'modules.tool_parser')

    Returns:
        True если перезагрузка удалась
    """
    if module_name not in sys.modules:
        return False

    try:
        importlib.reload(sys.modules[module_name])
        return True
    except Exception as e:
        logging.error(f"Hot reload failed for {module_name}: {e}")
        return False


def reload_zone(zone: str) -> dict[str, bool]:
    """Перезагрузить все модули указанной зоны.

    Args:
        zone: 'autonomous', 'supervised' или 'kernel'

    Returns:
        словарь {имя_модуля: успех}
    """
    if zone == "kernel":
        return {}

    modules = ZONE_MODULES.get(zone, [])
    results = {}

    for mod_name in modules:
        results[mod_name] = reload_module(mod_name)

    return results


def reload_all_autonomous() -> dict[str, bool]:
    """Перезагрузить все autonomous-модули."""
    return reload_zone("autonomous")


def reload_all_supervised() -> dict[str, bool]:
    """Перезагрузить все supervised-модули."""
    return reload_zone("supervised")


def reload_changed_files(file_paths: list[str]) -> dict[str, bool]:
    """Перезагрузить модули по изменившимся файлам.

    Автоматически определяет, какие модули нужно перезагрузить
    на основе путей к изменённым файлам.

    Args:
        file_paths: список путей к изменённым файлам

    Returns:
        словарь {имя_модуля: успех}
    """
    results = {}

    for filepath in file_paths:
        module_name = _filepath_to_module(filepath)
        if module_name:
            results[module_name] = reload_module(module_name)

    return results


def _filepath_to_module(filepath: str) -> Optional[str]:
    """Преобразовать путь к файлу в имя модуля Python.

    Примеры:
        modules/tool_parser.py → modules.tool_parser
        core/core.py → core.core
        agents/casual_agent.py → agents.casual_agent
    """
    # Нормализуем путь
    filepath = filepath.replace("\\", "/")

    # Убираем расширение .py
    if filepath.endswith(".py"):
        filepath = filepath[:-3]

    # Убираем ведущие ./
    if filepath.startswith("./"):
        filepath = filepath[2:]

    # Убираем __init__
    if filepath.endswith("/__init__"):
        filepath = filepath[:-9]

    # Конвертируем / в .
    module_name = filepath.replace("/", ".")

    # Проверяем, что модуль загружен
    if module_name in sys.modules:
        return module_name

    return None


def get_zone_for_file(filepath: str) -> Optional[str]:
    """Определить зону мутабельности для файла.

    Args:
        filepath: путь к файлу

    Returns:
        'kernel', 'supervised', 'autonomous' или None
    """
    filepath = filepath.replace("\\", "/")

    # Kernel — пока пусто
    # Supervised
    supervised_prefixes = ["_core.py", "core/", "core/core.py",
                           "core/core_tools.py", "core/__init__.py"]
    for prefix in supervised_prefixes:
        if filepath.startswith(prefix) or filepath == prefix:
            return "supervised"

    # Autonomous
    autonomous_prefixes = [
        "core_tools.py", "agents/", "modules/", "prompts/",
        "prompts.json", "mcp_server_", "mcp_servers/",
    ]
    for prefix in autonomous_prefixes:
        if filepath.startswith(prefix) or filepath == prefix:
            return "autonomous"

    return None


def hot_reload_selfmod(file_paths: list[str]) -> dict[str, bool]:
    """Полный цикл hot reload для самоизменения.

    1. Определяет зону для каждого файла
    2. Перезагружает модули autonomous-зоны сразу
    3. Для supervised — только логирует (требует подтверждения человека)

    Args:
        file_paths: список изменённых файлов

    Returns:
        словарь {имя_модуля: успех}
    """
    results = {}

    for filepath in file_paths:
        zone = get_zone_for_file(filepath)
        module_name = _filepath_to_module(filepath)

        if zone == "kernel":
            continue  # kernel не перегружается

        if zone == "supervised":
            # supervised требует подтверждения — только логируем
            if module_name:
                results[module_name] = False
            continue

        if zone == "autonomous" and module_name:
            success = reload_module(module_name)
            results[module_name] = success

    return results