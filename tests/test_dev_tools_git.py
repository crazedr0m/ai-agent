# -*- coding: utf-8 -*-
# tests/test_dev_tools_git.py — Тесты run_command, git_status, git_diff, git_commit

import unittest
from unittest.mock import patch, MagicMock
import subprocess

from tests import *  # noqa: sys.path


class TestRunCommand(unittest.TestCase):
    """Тесты для dev_tools.run_command()."""

    @patch("modules.dev_tools.confirm_action", return_value=True)
    def test_command_success(self, mock_confirm):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "hello world"
        mock_result.stderr = ""
        with patch("subprocess.run", return_value=mock_result):
            from modules.dev_tools import run_command
            result = run_command("echo hello")
        self.assertIn("✅", result)
        self.assertIn("hello world", result)

    @patch("modules.dev_tools.confirm_action", return_value=True)
    def test_command_with_stderr(self, mock_confirm):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "error msg"
        with patch("subprocess.run", return_value=mock_result):
            from modules.dev_tools import run_command
            result = run_command("failing cmd")
        self.assertIn("error msg", result)

    @patch("modules.dev_tools.confirm_action", return_value=True)
    def test_command_empty_output(self, mock_confirm):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        with patch("subprocess.run", return_value=mock_result):
            from modules.dev_tools import run_command
            result = run_command("silent cmd")
        self.assertIn("пустой вывод", result)

    @patch("modules.dev_tools.confirm_action", return_value=True)
    def test_command_timeout(self, mock_confirm):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 60)):
            from modules.dev_tools import run_command
            result = run_command("slow cmd", timeout=60)
        self.assertIn("таймаут", result)

    @patch("modules.dev_tools.confirm_action", return_value=False)
    def test_command_denied(self, mock_confirm):
        from modules.dev_tools import run_command
        result = run_command("echo hi")
        self.assertIn("❌", result)


class TestGitStatus(unittest.TestCase):
    """Тесты для git_status()."""

    @patch("subprocess.run")
    def test_git_status_clean(self, mock_run):
        mock_status = MagicMock()
        mock_status.returncode = 0
        mock_status.stdout = ""
        mock_branch = MagicMock()
        mock_branch.returncode = 0
        mock_branch.stdout = "main\n"
        mock_run.side_effect = [mock_status, mock_branch]

        from modules.dev_tools import git_status
        result = git_status()
        self.assertIn("main", result)
        self.assertIn("Чистое", result)

    @patch("subprocess.run")
    def test_git_status_with_changes(self, mock_run):
        mock_status = MagicMock()
        mock_status.returncode = 0
        mock_status.stdout = " M file.py\n"
        mock_branch = MagicMock()
        mock_branch.returncode = 0
        mock_branch.stdout = "feat\n"
        mock_run.side_effect = [mock_status, mock_branch]

        from modules.dev_tools import git_status
        result = git_status()
        self.assertIn("file.py", result)

    @patch("subprocess.run", side_effect=Exception("no git"))
    def test_git_status_error(self, mock_run):
        from modules.dev_tools import git_status
        result = git_status()
        self.assertIn("Ошибка", result)


class TestGitDiff(unittest.TestCase):
    """Тесты для git_diff()."""

    @patch("subprocess.run")
    def test_git_diff_unstaged(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "diff --git a/file.py b/file.py"
        mock_run.return_value = mock_result

        from modules.dev_tools import git_diff
        result = git_diff(staged=False)
        self.assertIn("diff --git", result)
        args = mock_run.call_args[0][0]
        self.assertEqual(args, ["git", "diff"])

    @patch("subprocess.run")
    def test_git_diff_staged(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "diff --git a/f.py b/f.py"
        mock_run.return_value = mock_result

        from modules.dev_tools import git_diff
        result = git_diff(staged=True)
        self.assertIn("diff --git", result)
        args = mock_run.call_args[0][0]
        self.assertIn("--staged", args)

    @patch("subprocess.run")
    def test_git_diff_no_changes(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        from modules.dev_tools import git_diff
        result = git_diff()
        self.assertEqual(result, "Нет изменений")

    @patch("subprocess.run")
    def test_git_diff_not_a_repo(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        from modules.dev_tools import git_diff
        result = git_diff()
        self.assertIn("Не git-репозиторий", result)


class TestGitCommit(unittest.TestCase):
    """Тесты для git_commit()."""

    @patch("modules.dev_tools.confirm_action", return_value=True)
    @patch("subprocess.run")
    def test_commit_with_add_all(self, mock_run, mock_confirm):
        mock_add = MagicMock()
        mock_commit = MagicMock()
        mock_commit.returncode = 0
        mock_commit.stdout = "[main abc1234] message"
        mock_run.side_effect = [mock_add, mock_commit]

        from modules.dev_tools import git_commit
        result = git_commit("message", add_all=True)
        self.assertIn("✅", result)
        self.assertEqual(mock_run.call_count, 2)

    @patch("modules.dev_tools.confirm_action", return_value=True)
    @patch("subprocess.run")
    def test_commit_without_add_all(self, mock_run, mock_confirm):
        mock_commit = MagicMock()
        mock_commit.returncode = 0
        mock_commit.stdout = "done"
        mock_run.return_value = mock_commit

        from modules.dev_tools import git_commit
        git_commit("msg", add_all=False)
        self.assertEqual(mock_run.call_count, 1)

    @patch("modules.dev_tools.confirm_action", return_value=True)
    @patch("subprocess.run")
    def test_commit_failure(self, mock_run, mock_confirm):
        mock_commit = MagicMock()
        mock_commit.returncode = 1
        mock_commit.stderr = "nothing to commit"
        mock_run.return_value = mock_commit

        from modules.dev_tools import git_commit
        result = git_commit("bad")
        self.assertIn("❌", result)

    @patch("modules.dev_tools.confirm_action", return_value=False)
    def test_commit_denied(self, mock_confirm):
        from modules.dev_tools import git_commit
        result = git_commit("secret")
        self.assertIn("❌", result)


if __name__ == "__main__":
    unittest.main()