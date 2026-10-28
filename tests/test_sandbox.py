# -*- coding: utf-8 -*-
# tests/test_sandbox.py -- Тесты для Sandbox (Фаза 4.2)

import unittest
import unittest.mock
import os
import tempfile
import shutil
import json

from tests import *  # noqa: sys.path


class TestSandboxError(unittest.TestCase):
    """SandboxError."""

    def test_sandbox_error_is_exception(self):
        from modules.sandbox import SandboxError
        self.assertTrue(issubclass(SandboxError, Exception))

    def test_sandbox_error_message(self):
        from modules.sandbox import SandboxError
        err = SandboxError("test error")
        self.assertIn("test error", str(err))


class TestSandboxInit(unittest.TestCase):
    """Sandbox.__init__."""

    def test_default_repo_path(self):
        from modules.sandbox import Sandbox
        sb = Sandbox("test_change")
        self.assertEqual(sb.repo_path, os.getcwd())
        self.assertEqual(sb.name, "test_change")
        self.assertFalse(sb._accepted)

    def test_custom_repo_path(self):
        from modules.sandbox import Sandbox
        sb = Sandbox("test", repo_path="/tmp")
        self.assertEqual(sb.repo_path, "/tmp")

    def test_branch_name_format(self):
        from modules.sandbox import Sandbox
        sb = Sandbox("test_change")
        self.assertIn("selfmod/test_change_", sb.branch_name)



class TestSandboxAddFile(unittest.TestCase):
    """Sandbox.add_file."""

    def test_add_file_appends(self):
        from modules.sandbox import Sandbox
        sb = Sandbox("test")
        sb.add_file("file1.py")
        sb.add_file("file2.py")
        self.assertEqual(sb._files_to_commit, ["file1.py", "file2.py"])


class TestSandboxIsGitRepo(unittest.TestCase):
    """Sandbox._is_git_repo."""

    def test_git_repo_returns_true(self):
        from modules.sandbox import Sandbox
        with unittest.mock.patch.object(Sandbox, "_git", return_value=".git"):
            sb = Sandbox("test")
            self.assertTrue(sb._is_git_repo())

    def test_non_git_repo_returns_false(self):
        from modules.sandbox import Sandbox, SandboxError
        with unittest.mock.patch.object(Sandbox, "_git",
                                        side_effect=SandboxError("no git")):
            sb = Sandbox("test")
            self.assertFalse(sb._is_git_repo())


class TestSandboxGit(unittest.TestCase):
    """Sandbox._git."""

    def test_git_version_returns_stdout(self):
        from modules.sandbox import Sandbox
        sb = Sandbox("test", repo_path="/tmp")
        result = sb._git("version")
        self.assertIn("git", result)

    def test_bad_command_raises_sandbox_error(self):
        from modules.sandbox import Sandbox, SandboxError
        sb = Sandbox("test", repo_path="/tmp")
        with self.assertRaises(SandboxError):
            sb._git("nonexistent-command-xyz")


class TestSandboxAcceptReject(unittest.TestCase):
    """Sandbox.accept, .reject (mocked git)."""

    def test_accept_marked(self):
        from modules.sandbox import Sandbox
        with unittest.mock.patch.object(Sandbox, "_git", return_value=""):
            with unittest.mock.patch.object(Sandbox, "_write_report"):
                sb = Sandbox("test")
                sb._accepted = False
                sb._original_branch = "main"
                sb.add_file("test.py")
                sb.accept()
                self.assertTrue(sb._accepted)

    def test_double_accept_no_effect(self):
        from modules.sandbox import Sandbox
        with unittest.mock.patch.object(Sandbox, "_git", return_value=""):
            with unittest.mock.patch.object(Sandbox, "_write_report"):
                sb = Sandbox("test")
                sb._accepted = True
                sb.accept()
                # Не должно быть повторного git add/commit
                self.assertTrue(sb._accepted)

    def test_reject_without_accept(self):
        from modules.sandbox import Sandbox
        with unittest.mock.patch.object(Sandbox, "_git", return_value=""):
            sb = Sandbox("test")
            sb._original_branch = "main"
            sb.reject()
            self.assertFalse(sb._accepted)

    def test_reject_after_accept_skips(self):
        from modules.sandbox import Sandbox
        with unittest.mock.patch.object(Sandbox, "_git", return_value=""):
            sb = Sandbox("test")
            sb._accepted = True
            sb.reject()
            self.assertTrue(sb._accepted)


class TestSandboxGetDiff(unittest.TestCase):
    """Sandbox.get_diff."""

    def test_get_diff_returns_string(self):
        from modules.sandbox import Sandbox
        with unittest.mock.patch.object(Sandbox, "_git", return_value="dummy diff"):
            sb = Sandbox("test")
            result = sb.get_diff()
            self.assertEqual(result, "dummy diff")


class TestSandboxWriteReport(unittest.TestCase):
    """Sandbox._write_report."""

    def tearDown(self):
        shutil.rmtree("traces", ignore_errors=True)

    def test_report_created(self):
        from modules.sandbox import Sandbox
        with unittest.mock.patch.object(Sandbox, "_git", return_value=""):
            sb = Sandbox("test")
            sb._original_branch = "main"
            sb._write_report("test commit")
            report_dir = os.path.join("traces", "selfmod")
            self.assertTrue(os.path.exists(report_dir))
            files = os.listdir(report_dir)
            self.assertGreater(len(files), 0)
            with open(os.path.join(report_dir, files[0])) as f:
                data = json.load(f)
            self.assertEqual(data["name"], "test")
            self.assertEqual(data["status"], "accepted")


if __name__ == "__main__":
    unittest.main()