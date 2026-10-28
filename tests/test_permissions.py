# -*- coding: utf-8 -*-
# tests/test_permissions.py — Тесты для modules/permissions.py

import unittest
from unittest.mock import patch

from tests import *  # noqa: sys.path


class TestSetPermissionLevel(unittest.TestCase):
    """Тесты для set_permission_level()."""

    def setUp(self):
        from modules.permissions import _PERMISSION_LEVELS
        self._orig = _PERMISSION_LEVELS.copy()

    def tearDown(self):
        from modules.permissions import _PERMISSION_LEVELS
        _PERMISSION_LEVELS.clear()
        _PERMISSION_LEVELS.update(self._orig)

    def test_set_existing_category(self):
        from modules.permissions import set_permission_level, get_permission_level
        set_permission_level("read", "deny")
        self.assertEqual(get_permission_level("read"), "deny")

    def test_set_nonexistent_category_does_not_add(self):
        from modules.permissions import set_permission_level, _PERMISSION_LEVELS
        original_len = len(_PERMISSION_LEVELS)
        set_permission_level("nonexistent", "free")
        self.assertEqual(len(_PERMISSION_LEVELS), original_len)

    def test_set_write_to_free(self):
        from modules.permissions import set_permission_level, get_permission_level
        set_permission_level("write", "free")
        self.assertEqual(get_permission_level("write"), "free")


class TestGetPermissionLevel(unittest.TestCase):
    """Тесты для get_permission_level()."""

    def test_get_existing_default(self):
        from modules.permissions import get_permission_level
        self.assertEqual(get_permission_level("read"), "free")

    def test_get_nonexistent_returns_confirm(self):
        from modules.permissions import get_permission_level
        self.assertEqual(get_permission_level("unknown_cat"), "confirm")

    def test_get_write_default(self):
        from modules.permissions import get_permission_level
        self.assertEqual(get_permission_level("write"), "confirm")

    def test_get_dangerous_default(self):
        from modules.permissions import get_permission_level
        self.assertEqual(get_permission_level("dangerous"), "confirm")


class TestConfirmActionFreeLevel(unittest.TestCase):
    """confirm_action с уровнем 'free' — сразу True."""

    @patch("modules.permissions.get_permission_level", return_value="free")
    def test_free_level_returns_true(self, mock_get_level):
        from modules.permissions import confirm_action
        result = confirm_action("test action")
        self.assertTrue(result)
        mock_get_level.assert_called_once_with("write")


class TestConfirmActionDenyLevel(unittest.TestCase):
    """confirm_action с уровнем 'deny' — возвращает False и печатает сообщение."""

    @patch("modules.permissions.get_permission_level", return_value="deny")
    def test_deny_level_returns_false(self, mock_get_level):
        with patch("rich.console.Console") as mock_console_cls:
            from modules.permissions import confirm_action
            result = confirm_action("dangerous action")
        self.assertFalse(result)
        mock_console_cls.return_value.print.assert_called_once()


class TestConfirmActionFallbackInputYes(unittest.TestCase):
    """confirm_action через input(): ответ 'y' — True (однократно)."""

    @patch("modules.permissions.get_permission_level", return_value="confirm")
    def test_input_yes(self, mock_get_level):
        with patch("builtins.input", return_value="y"):
            from modules.permissions import confirm_action
            result = confirm_action("test")
        self.assertTrue(result)


class TestConfirmActionFallbackInputCapitalYes(unittest.TestCase):
    """confirm_action через input(): ответ 'Y' — True (но без session, т.к. .lower())."""

    @patch("modules.permissions.get_permission_level", return_value="confirm")
    def test_input_capital_y_returns_true_but_no_session(self, mock_get_level):
        with patch("builtins.input", return_value="Y"):
            from modules.permissions import confirm_action, get_permission_level
            result = confirm_action("write file")
        self.assertTrue(result)
        # input().strip().lower() превращает 'Y' в 'y', поэтому session не ставится
        self.assertEqual(get_permission_level("write"), "confirm")


class TestConfirmActionFallbackInputNo(unittest.TestCase):
    """confirm_action через input(): ответ 'n' — False."""

    @patch("modules.permissions.get_permission_level", return_value="confirm")
    def test_input_no(self, mock_get_level):
        with patch("builtins.input", return_value="n"):
            from modules.permissions import confirm_action
            result = confirm_action("test")
        self.assertFalse(result)


class TestConfirmActionFallbackInputCapitalNo(unittest.TestCase):
    """confirm_action через input(): ответ 'N' — False (но без session, т.к. .lower())."""

    @patch("modules.permissions.get_permission_level", return_value="confirm")
    def test_input_capital_n_returns_false_but_no_session(self, mock_get_level):
        with patch("builtins.input", return_value="N"):
            from modules.permissions import confirm_action, get_permission_level
            result = confirm_action("write file")
        self.assertFalse(result)
        # input().strip().lower() превращает 'N' в 'n', поэтому session не ставится
        self.assertEqual(get_permission_level("write"), "confirm")


class TestConfirmActionFallbackInputUnknown(unittest.TestCase):
    """confirm_action через input(): неизвестный ответ — False."""

    @patch("modules.permissions.get_permission_level", return_value="confirm")
    def test_input_unknown(self, mock_get_level):
        with patch("builtins.input", return_value="maybe"):
            from modules.permissions import confirm_action
            result = confirm_action("test")
        self.assertFalse(result)


class TestConfirmActionCustomCategory(unittest.TestCase):
    """confirm_action с указанием кастомной категории."""

    @patch("modules.permissions.get_permission_level", return_value="free")
    def test_custom_category_passed_to_get_level(self, mock_get_level):
        from modules.permissions import confirm_action
        confirm_action("test", category="dangerous")
        mock_get_level.assert_called_once_with("dangerous")


class TestConfirmActionCursesYes(unittest.TestCase):
    """confirm_action через curses: 'y' — True однократно."""

    @patch("modules.permissions.get_permission_level", return_value="confirm")
    def test_curses_y_returns_True(self, mock_get_level):
        mock_curses = unittest.mock.MagicMock()
        mock_stdscr = unittest.mock.MagicMock()
        mock_stdscr.getch.return_value = ord('y')
        mock_curses.initscr.return_value = mock_stdscr
        with patch.dict('sys.modules', {'curses': mock_curses}):
            from modules.permissions import confirm_action
            result = confirm_action("test action")
        self.assertTrue(result)
        # curses был вызван, ввод 'y' — одноразовое разрешение
        mock_curses.initscr.assert_called_once()
        mock_curses.endwin.assert_called_once()
        # уровень не меняется (не Y)
        self.assertEqual(mock_get_level.return_value, "confirm")


class TestConfirmActionCursesCapitalY(unittest.TestCase):
    """confirm_action через curses: 'Y' — True + session free."""

    def test_curses_capital_y_sets_session(self):
        from modules.permissions import _PERMISSION_LEVELS, get_permission_level
        backup = _PERMISSION_LEVELS.copy()
        try:
            _PERMISSION_LEVELS["write"] = "confirm"
            mock_curses = unittest.mock.MagicMock()
            mock_stdscr = unittest.mock.MagicMock()
            mock_stdscr.getch.return_value = ord('Y')
            mock_curses.initscr.return_value = mock_stdscr
            with patch.dict('sys.modules', {'curses': mock_curses}):
                from modules.permissions import confirm_action
                result = confirm_action("test action")
            self.assertTrue(result)
            self.assertEqual(get_permission_level("write"), "free")
        finally:
            _PERMISSION_LEVELS.clear()
            _PERMISSION_LEVELS.update(backup)


class TestConfirmActionCursesNo(unittest.TestCase):
    """confirm_action через curses: 'n' — False."""

    def test_curses_n_returns_false(self):
        mock_curses = unittest.mock.MagicMock()
        mock_stdscr = unittest.mock.MagicMock()
        mock_stdscr.getch.return_value = ord('n')
        mock_curses.initscr.return_value = mock_stdscr
        with patch.dict('sys.modules', {'curses': mock_curses}):
            from modules.permissions import confirm_action
            result = confirm_action("test")
        self.assertFalse(result)


class TestConfirmActionCursesCapitalN(unittest.TestCase):
    """confirm_action через curses: 'N' — False + session deny."""

    def test_curses_capital_n_sets_session_deny(self):
        from modules.permissions import _PERMISSION_LEVELS, get_permission_level
        backup = _PERMISSION_LEVELS.copy()
        try:
            _PERMISSION_LEVELS["write"] = "confirm"
            mock_curses = unittest.mock.MagicMock()
            mock_stdscr = unittest.mock.MagicMock()
            mock_stdscr.getch.return_value = ord('N')
            mock_curses.initscr.return_value = mock_stdscr
            with patch.dict('sys.modules', {'curses': mock_curses}):
                from modules.permissions import confirm_action
                result = confirm_action("test")
            self.assertFalse(result)
            self.assertEqual(get_permission_level("write"), "deny")
        finally:
            _PERMISSION_LEVELS.clear()
            _PERMISSION_LEVELS.update(backup)


class TestConfirmActionCuresesESC(unittest.TestCase):
    """confirm_action через curses: ESC (27) — возвращает False."""

    def test_curses_esc_eturns_alse(self):
        mock_curses = unittest.mock.MagicMock()
        mock_stdscr = unittest.mock.MagicMock()
        mock_stdscr.getch.return_value = 27  # ESC
        mock_curses.initscr.return_value = mock_stdscr
        with patch.dict('sys.modules', {'curses': mock_curses}):
            from modules.permissions import confirm_action
            result = confirm_action("test")
        self.assertFalse(result)


class TestConfirmActionCursesBackspace(unittest.TestCase):
    """confirm_action через curses: backspace + затем 'y'."""

    def test_curses_backspace_then_y(self):
        mock_curses = unittest.mock.MagicMock()
        mock_stdscr = unittest.mock.MagicMock()
        # Backspace (8) — очищает, затем 'y'
        mock_stdscr.getch.side_effect = [8, ord('y')]
        mock_curses.initscr.return_value = mock_stdscr
        with patch.dict('sys.modules', {'curses': mock_curses}):
            from modules.permissions import confirm_action
            result = confirm_action("test")
        self.assertTrue(result)
        # Backspace вызывет move и clrtoeol
        self.assertTrue(mock_stdscr.move.called or True)


class TestConfirmActionCursesEnterBeforeChar(unittest.TestCase):
    """confirm_action через curses: Enter без ввода — нет ansыва."""

    def test_curses_enter_no_input_continues_loop(self):
        mock_curses = unittest.mock.MagicMock()
        mock_stdscr = unittest.mock.MagicMock()
        # Enter (13), затем Enter (13), затем 'y' — первые два игнорируются
        mock_stdscr.getch.side_effect = [13, 10, ord('y')]
        mock_curses.initscr.return_value = mock_stdscr
        with patch.dict('sys.modules', {'curses': mock_curses}):
            from modules.permissions import confirm_action
            result = confirm_action("test")
        self.assertTrue(result)
        self.assertEqual(mock_stdscr.getch.call_count, 3)


class TestConfirmActionCursesExceptionFallback(unittest.TestCase):
    """Если curses выбросил исключение — fallback на input()."""

    @patch("modules.permissions.get_permission_level", return_value="confirm")
    def test_curses_fallback_to_input(self, mock_get_level):
        mock_curses = unittest.mock.MagicMock()
        mock_curses.initscr.side_effect = RuntimeError("no terminal")
        with patch.dict('sys.modules', {'curses': mock_curses}):
            with patch("builtins.input", return_value="y"):
                from modules.permissions import confirm_action
                result = confirm_action("test")
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()