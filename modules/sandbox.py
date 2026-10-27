# -*- coding: utf-8 -*-
# modules/sandbox.py — Песочница изменений (Фаза 4.2)
#
# Создаёт отдельную git-ветку для каждой попытки самоизменения.
# Позволяет применить, откатить или зафиксировать изменения.
#
# Использование:
#     from modules.sandbox import Sandbox
#     with Sandbox("fix-parser") as sb:
#         # вносим изменения
#         sb.add_file("modules/tool_parser.py")
#         # если всё ок — sb.accept()
#         # если нет — sb.reject() (авто-откат при выходе из with)
#     # после with ветка уже не активна

import os
import subprocess
import sys
from datetime import datetime
from typing import Optional


class SandboxError(Exception):
    """Ошибка песочницы."""


class Sandbox:
    """Песочница изменений на базе git-ветки.

    При входе в контекст:
    - Проверяет, что репозиторий чист (нет незакоммиченных изменений)
    - Создаёт новую ветку от текущей

    При выходе:
    - Если accept() не был вызван — автоматический откат (reject)
    - Переключается обратно на исходную ветку
    """

    def __init__(self, name: str, base_branch: str = None,
                 repo_path: str = None):
        """
        Args:
            name: название изменения (используется как имя ветки)
            base_branch: от какой ветки ответвляться (по умолчанию текущая)
            repo_path: путь к репозиторию (по умолчанию CWD)
        """
        self.name = name
        self.branch_name = f"selfmod/{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.base_branch = base_branch
        self.repo_path = repo_path or os.getcwd()
        self._accepted = False
        self._original_branch = None
        self._files_to_commit = []

    # ─────────────────────────────────────────────
    # Публичные методы
    # ─────────────────────────────────────────────

    def add_file(self, file_path: str):
        """Добавить файл для коммита в песочнице.

        Args:
            file_path: путь к файлу относительно корня репозитория
        """
        self._files_to_commit.append(file_path)

    def accept(self, message: str = None):
        """Принять изменения: закоммитить в ветку и записать отчёт.

        Args:
            message: сообщение коммита (по умолчанию генерируется)
        """
        if self._accepted:
            return

        if not self._files_to_commit:
            self._git("add", "-A")  # добавляем всё
        else:
            for f in self._files_to_commit:
                self._git("add", f)

        commit_msg = message or f"🤖 self-mod: {self.name}"
        self._git("commit", "-m", commit_msg, "--allow-empty")
        self._accepted = True

        # Пишем отчёт
        self._write_report(commit_msg)

    def reject(self):
        """Отклонить изменения: откатить ветку."""
        if self._accepted:
            return
        # Возвращаемся на исходную ветку — изменения в sandbox-ветке просто
        # остаются незакоммиченными и исчезают при переключении
        self._git("checkout", self._original_branch)
        # Удаляем ветку
        self._git("branch", "-D", self.branch_name)

    def get_diff(self) -> str:
        """Получить diff изменений в песочнице."""
        result = self._git("diff", "--stat")
        return result

    # ─────────────────────────────────────────────
    # Контекстный менеджер
    # ─────────────────────────────────────────────

    def __enter__(self) -> "Sandbox":
        # Проверяем git
        if not self._is_git_repo():
            raise SandboxError(f"{self.repo_path} не git-репозиторий")

        # Проверяем, что репозиторий чист
        status = self._git("status", "--porcelain")
        if status.strip():
            raise SandboxError(
                "Репозиторий не чист. Закоммитьте или stash изменения перед "
                "началом самоизменения."
            )

        # Запоминаем текущую ветку
        self._original_branch = self._git("rev-parse", "--abbrev-ref", "HEAD").strip()

        # Создаём новую ветку
        self._git("checkout", "-b", self.branch_name)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Исключение — откатываем
            if not self._accepted:
                self._reject_cleanup()
            return False

        if not self._accepted:
            self._reject_cleanup()

    # ─────────────────────────────────────────────
    # Приватные методы
    # ─────────────────────────────────────────────

    def _reject_cleanup(self):
        """Откат без сообщения пользователю."""
        try:
            self._git("checkout", self._original_branch)
            self._git("branch", "-D", self.branch_name)
        except Exception:
            pass

    def _is_git_repo(self) -> bool:
        try:
            self._git("rev-parse", "--git-dir")
            return True
        except SandboxError:
            return False

    def _git(self, *args: str) -> str:
        """Выполнить git-команду."""
        cmd = ["git"] + list(args)
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_path,
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise SandboxError(
                f"git {' '.join(args)} failed:\n"
                f"stdout: {e.stdout}\n"
                f"stderr: {e.stderr}"
            )

    def _write_report(self, commit_msg: str):
        """Записать отчёт о самоизменении."""
        report_dir = os.path.join(self.repo_path, "traces", "selfmod")
        os.makedirs(report_dir, exist_ok=True)

        report = {
            "name": self.name,
            "branch": self.branch_name,
            "base_branch": self._original_branch,
            "commit_message": commit_msg,
            "files": self._files_to_commit,
            "timestamp": datetime.now().isoformat(),
            "status": "accepted",
        }

        import json
        report_path = os.path.join(
            report_dir,
            f"{self.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        )
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)