# -*- coding: utf-8 -*-
# tests/test_sandbox.py — Тесты для Sandbox (Фаза 4.2)

import unittest
import os
import tempfile
import shutil

from tests import *  # noqa: sys.path


class TestPhase4Sandbox(unittest.TestCase):
    """Тесты для Sandbox (Фаза 4.2)."""

    def test_sandbox_not_git_repo(self):
        """Sandbox падает если не git-репозиторий."""
        tmpdir = tempfile.mkdtemp()
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            from modules.sandbox import Sandbox, SandboxError
            with self.assertRaises(SandboxError):
                with Sandbox("test"):
                    pass
        finally:
            os.chdir(old_cwd)
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_sandbox_error_class(self):
        """SandboxError — исключение."""
        from modules.sandbox import SandboxError
        e = SandboxError("test error")
        self.assertIn("test error", str(e))


if __name__ == "__main__":
    unittest.main()