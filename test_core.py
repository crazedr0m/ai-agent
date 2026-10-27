#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# test_core.py — Корневой раннер тестов
#
# Запускает все тесты из пакета tests/ через unittest discover.
#
# Использование:
#   python test_core.py              # все тесты
#   python -m unittest discover      # то же самое
#
# Правила:
# - unittest (не pytest)
# - subprocess.run() для внешних тестов
# - returncode == 0 как критерий успеха

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == '__main__':
    test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tests')
    suite = unittest.TestLoader().discover(test_dir, pattern='test_*.py')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)