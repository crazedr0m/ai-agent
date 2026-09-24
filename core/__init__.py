# -*- coding: utf-8 -*-
# core/__init__.py
#
# Делает import core доступным: объединяет _core.py + core/core_tools + core/core
# в единый модуль core. Все старые импорты import core продолжают работать.
#
# Важно: sys.modules['core'] остаётся пакетом, чтобы импорты внутри core/ работали.
# Атрибуты из _core.py копируются в этот пакет.

import importlib.util
import sys
import os

# 1. Загружаем _core.py (бывший core.py) как отдельный модуль _root_core
_core_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_core.py")
_spec = importlib.util.spec_from_file_location("_root_core", _core_path)
_root_core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_root_core)
sys.modules['_root_core'] = _root_core  # регистрируем, чтобы не перегружался

# 2. Импортируем новые компоненты (теперь core — это пакет, всё ОК)
from .core_tools import ToolRegistry, register_tool, get_tool, _GLOBAL_REGISTRY
from .core import BaseAgent, ReActEngine

# 3. Копируем все публичные атрибуты из _root_core в текущий (пакетный) модуль
_this = sys.modules[__name__]
for _attr_name in dir(_root_core):
    if not _attr_name.startswith('_'):
        try:
            setattr(_this, _attr_name, getattr(_root_core, _attr_name))
        except Exception:
            pass  # некоторые built-in атрибуты могут не ставиться

# 4. Добавляем новые компоненты
_this.ToolRegistry = ToolRegistry
_this.register_tool = register_tool
_this.get_tool = get_tool
_this._GLOBAL_REGISTRY = _GLOBAL_REGISTRY
_this.BaseAgent = BaseAgent
_this.ReActEngine = ReActEngine