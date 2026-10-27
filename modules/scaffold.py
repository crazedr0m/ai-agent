# -*- coding: utf-8 -*-
# modules/scaffold.py — Self-extension: шаблон нового инструмента/модуля (Фаза 4.5)
#
# Позволяет агенту создавать новые инструменты и модули по шаблону
# с обязательным тестом и прогоном через гейт.
#
# Использование:
#     from modules.scaffold import Scaffold
#     sc = Scaffold()
#     sc.create_tool("my_tool", "my_tool.py", "Мой инструмент")
#     sc.create_module("my_module", "my_module.py", "Мой модуль")
#     sc.create_mcp_server("my_server", "mcp_server_my.py", "Мой MCP-сервер")

import os
import json
from datetime import datetime
from typing import Optional


class ScaffoldError(Exception):
    """Ошибка scaffold."""


class Scaffold:
    """Генератор кода для новых инструментов и модулей.

    Создаёт файл с шаблоном, тест и регистрирует инструмент.
    """

    def __init__(self, repo_path: str = None):
        self.repo_path = repo_path or os.getcwd()

    # ─────────────────────────────────────────────
    # Публичные методы
    # ─────────────────────────────────────────────

    def create_tool(self, name: str, filename: str = None,
                    description: str = "") -> str:
        """Создать новый инструмент.

        Args:
            name: имя инструмента (snake_case)
            filename: имя файла (по умолчанию {name}.py)
            description: описание инструмента

        Returns:
            путь к созданному файлу
        """
        filename = filename or f"{name}.py"
        filepath = os.path.join(self.repo_path, filename)

        if os.path.exists(filepath):
            raise ScaffoldError(f"Файл {filepath} уже существует")

        content = self._tool_template(name, description)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        # Создаём тест
        self._create_tool_test(name, filename)

        return filepath

    def create_module(self, name: str, filename: str = None,
                      description: str = "") -> str:
        """Создать новый модуль в modules/.

        Args:
            name: имя модуля (snake_case)
            filename: имя файла (по умолчанию {name}.py)
            description: описание модуля

        Returns:
            путь к созданному файлу
        """
        filename = filename or f"{name}.py"
        filepath = os.path.join(self.repo_path, "modules", filename)

        if os.path.exists(filepath):
            raise ScaffoldError(f"Файл {filepath} уже существует")

        content = self._module_template(name, description)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        # Создаём тест
        self._create_module_test(name, filename)

        return filepath

    def create_mcp_server(self, name: str, filename: str = None,
                           description: str = "") -> str:
        """Создать новый MCP-сервер на FastMCP.

        Args:
            name: имя сервера (snake_case)
            filename: имя файла (по умолчанию mcp_server_{name}.py)
            description: описание сервера

        Returns:
            путь к созданному файлу
        """
        filename = filename or f"mcp_server_{name}.py"
        filepath = os.path.join(self.repo_path, filename)

        if os.path.exists(filepath):
            raise ScaffoldError(f"Файл {filepath} уже существует")

        content = self._mcp_server_template(name, description)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        # Создаём тест
        self._create_mcp_test(name, filename)

        return filepath

    # ─────────────────────────────────────────────
    # Шаблоны
    # ─────────────────────────────────────────────

    def _tool_template(self, name: str, description: str) -> str:
        return f'''# -*- coding: utf-8 -*-
# {name}.py — {description or name}
#
# Создан агентом через Scaffold ({datetime.now().strftime('%Y-%m-%d %H:%M')})
#
# Регистрация:
#     from core.core_tools import register_tool
#     @register_tool("{name}", "{description or name}")
#     def {name}(arg: str = "") -> str:
#         ...

from core.core_tools import register_tool


@register_tool("{name}", "{description or name}")
def {name}(arg: str = "") -> str:
    """{description or name}.

    Args:
        arg: аргумент инструмента

    Returns:
        результат выполнения
    """
    # TODO: реализовать логику инструмента
    return f"✅ {name} executed with arg={{arg}}"
'''

    def _module_template(self, name: str, description: str) -> str:
        return f'''# -*- coding: utf-8 -*-
# modules/{name}.py — {description or name}
#
# Создан агентом через Scaffold ({datetime.now().strftime('%Y-%m-%d %H:%M')})
#
# Использование:
#     from modules.{name} import ...


class {name.capitalize()}:
    """{description or name}."""

    def __init__(self):
        pass

    def run(self) -> str:
        """Запустить модуль."""
        # TODO: реализовать логику
        return f"✅ {{self.__class__.__name__}} executed"
'''

    def _mcp_server_template(self, name: str, description: str) -> str:
        return f'''# -*- coding: utf-8 -*-
# mcp_server_{name}.py — MCP-сервер: {description or name}
#
# Создан агентом через Scaffold ({datetime.now().strftime('%Y-%m-%d %H:%M')})
#
# Запуск:
#     python mcp_server_{name}.py  # stdio
#     python mcp_server_{name}.py --transport sse --port 3300

import argparse

from fastmcp import FastMCP

mcp = FastMCP(
    "{name}-server",
    instructions="{description or name}",
    version="1.0.0",
)


@mcp.tool()
def ping() -> str:
    """Проверка доступности сервера."""
    return "pong"


def main():
    parser = argparse.ArgumentParser(description="{description or name}")
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio")
    parser.add_argument("--port", type=int, default=3300)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    if args.transport == "sse":
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
'''

    # ─────────────────────────────────────────────
    # Тесты
    # ─────────────────────────────────────────────

    def _create_tool_test(self, name: str, filename: str):
        """Добавить тест для нового инструмента в test_core.py."""
        test_code = f'''
    def test_{name}(self):
        """{name} возвращает результат."""
        import {name.replace(".py", "")}
        result = {name.replace(".py", "")}.{name}("test")
        self.assertIn("executed", result)
'''
        self._append_to_test_file(test_code)

    def _create_module_test(self, name: str, filename: str):
        """Добавить тест для нового модуля в test_core.py."""
        test_code = f'''
    def test_{name}(self):
        """{name} запускается без ошибок."""
        from modules.{name} import {name.capitalize()}
        instance = {name.capitalize()}()
        result = instance.run()
        self.assertIn("executed", result)
'''
        self._append_to_test_file(test_code)

    def _create_mcp_test(self, name: str, filename: str):
        """Добавить тест для нового MCP-сервера в test_core.py."""
        test_code = f'''
    def test_mcp_{name}_ping(self):
        """MCP-сервер {name} отвечает на ping."""
        from mcp_server_{name} import ping
        result = ping()
        self.assertEqual(result, "pong")
'''
        self._append_to_test_file(test_code)

    def _append_to_test_file(self, test_code: str):
        """Добавить тест в test_core.py перед if __name__."""
        test_path = os.path.join(self.repo_path, "test_core.py")
        if not os.path.exists(test_path):
            return

        with open(test_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Вставляем перед последним классом или перед if __name__
        marker = 'if __name__ == "__main__":'
        if marker in content:
            # Вставляем тест в последний тестовый класс
            # Ищем последний class ...Test
            import re
            classes = list(re.finditer(r'^class (\w+Test|Test\w+)', content, re.MULTILINE))
            if classes:
                last_class = classes[-1]
                # Ищем конец последнего метода в этом классе
                class_end = self._find_method_end(content, last_class.end())
                insert_pos = class_end
                content = (
                    content[:insert_pos] +
                    test_code +
                    content[insert_pos:]
                )
            else:
                # Вставляем перед if __name__
                insert_pos = content.index(marker)
                content = (
                    content[:insert_pos] +
                    "\n\n" + test_code + "\n" +
                    content[insert_pos:]
                )
        else:
            content += "\n" + test_code

        with open(test_path, "w", encoding="utf-8") as f:
            f.write(content)

    def _find_method_end(self, content: str, start: int) -> int:
        """Найти конец последнего метода в классе."""
        lines = content[start:].split("\n")
        last_def = -1
        for i, line in enumerate(lines):
            if line.strip().startswith("def "):
                last_def = i
        if last_def >= 0:
            # Ищем следующую пустую строку после последнего def
            for i in range(last_def + 1, len(lines)):
                if not lines[i].strip() and i > last_def + 1:
                    return start + sum(len(l) + 1 for l in lines[:i])
        return len(content)