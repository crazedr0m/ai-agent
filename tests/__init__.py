# -*- coding: utf-8 -*-
# tests/__init__.py — Общая настройка тестового пакета
#
# Единственная обязанность: настроить sys.path для всего пакета,
# чтобы тесты могли импортировать core, modules, mcp_servers и т.д.

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))