# -*- coding: utf-8 -*-
# core/__init__.py
#
# Делает import core доступным: объединяет core.runtime + core.core_tools + core.core
# в единый модуль core. Все старые импорты import core продолжают работать.
#
# Единая загрузка ядра: core.runtime — единственный модуль с функциями ядра.
# Алиасы _core / _root_core в sys.modules сохраняют совместимость с hot_reload
# и легаси-кодом.

import sys

# 1. Единая загрузка ядра (единственное место, где живут функции ядра)
from . import runtime as _root_core

# 2. Алиасы для совместимости: hot_reload и легаси-импорты используют "_core"
sys.modules.setdefault("_root_core", _root_core)
sys.modules.setdefault("_core", _root_core)

# 3. Импортируем новые компоненты (core — пакет, всё ОК)
from .core_tools import ToolRegistry, register_tool, get_tool, _GLOBAL_REGISTRY
from .core import BaseAgent, ReActEngine

# 4. Копируем публичные атрибуты из runtime в текущий (пакетный) модуль
_this = sys.modules[__name__]
for _attr_name in dir(_root_core):
    if not _attr_name.startswith('_'):
        try:
            setattr(_this, _attr_name, getattr(_root_core, _attr_name))
        except Exception:
            pass  # некоторые built-in атрибуты могут не ставиться

# 5. Добавляем новые компоненты
_this.ToolRegistry = ToolRegistry
_this.register_tool = register_tool
_this.get_tool = get_tool
_this._GLOBAL_REGISTRY = _GLOBAL_REGISTRY
_this.BaseAgent = BaseAgent
_this.ReActEngine = ReActEngine
