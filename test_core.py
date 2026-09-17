# -*- coding: utf-8 -*-
import unittest
import os
import sys
import tempfile
import json

# Добавляем корень проекта в путь для импорта core
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import core


class TestLoadPrompt(unittest.TestCase):
    """Тесты для загрузки промптов."""

    def setUp(self):
        """Создаём временный prompts.json для тестов."""
        self.tmpdir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.tmpdir)

        # Создаём файл промпта на диске
        os.makedirs("prompts", exist_ok=True)
        with open("prompts/test_role.txt", "w", encoding="utf-8") as f:
            f.write("disk prompt content")

        # Создаём prompts.json с file_path
        self.config_with_file = {
            "test_role": {
                "file_path": "prompts/test_role.txt",
                "description": "Test prompt on disk",
                "mutability": "autonomous"
            }
        }
        with open("prompts.json", "w", encoding="utf-8") as f:
            json.dump(self.config_with_file, f, indent=2, ensure_ascii=False)

    def tearDown(self):
        os.chdir(self.original_dir)
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_load_prompt_from_file(self):
        """Загрузка промпта из файла на диске."""
        result = core.load_prompt_from_file("test_role")
        self.assertEqual(result, "disk prompt content")

    def test_load_prompt_fallback_to_inline(self):
        """Загрузка промпта из inline поля (без file_path)."""
        # Создаём конфиг без file_path
        config_inline = {
            "inline_role": {
                "prompt": "inline prompt content",
                "description": "Inline prompt",
                "mutability": "autonomous"
            }
        }
        with open("prompts.json", "w", encoding="utf-8") as f:
            json.dump(config_inline, f, indent=2, ensure_ascii=False)

        result = core.load_prompt("inline_role")
        self.assertEqual(result, "inline prompt content")


class TestUpdatePromptFile(unittest.TestCase):
    """Тесты для обновления промптов."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.tmpdir)
        os.makedirs("prompts", exist_ok=True)

    def tearDown(self):
        os.chdir(self.original_dir)
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_update_immutable_blocked(self):
        """Попытка обновить immutable промпт блокируется ядром."""
        config = {
            "immutable_role": {
                "file_path": "prompts/immutable_role.txt",
                "description": "Protected prompt",
                "mutability": "immutable"
            }
        }
        with open("prompts.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        result = core.update_prompt_file("immutable_role", "new content")
        self.assertFalse(result)

    def test_update_autonomous_success(self):
        """Обновление autonomous промпта проходит успешно."""
        with open("prompts/auto_role.txt", "w", encoding="utf-8") as f:
            f.write("old content")

        config = {
            "auto_role": {
                "file_path": "prompts/auto_role.txt",
                "description": "Auto-updatable prompt",
                "mutability": "autonomous"
            }
        }
        with open("prompts.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        result = core.update_prompt_file("auto_role", "new content")
        self.assertTrue(result)

        with open("prompts/auto_role.txt", "r") as f:
            self.assertEqual(f.read(), "new content")


class TestParseModelTools(unittest.TestCase):
    """Тесты для парсинга инструментов модели."""

    def test_no_tool_call(self):
        """Если инструмент не вызван — возвращается (False, '')."""
        response = "Просто текстовый ответ без вызова инструментов."
        has_tool, result = core.execute_model_tools(response)
        self.assertFalse(has_tool)
        self.assertEqual(result, "")

    def test_unknown_tool(self):
        """Неизвестный инструмент возвращает ошибку."""
        response = '<call name="unknown_tool">arg</call>'
        has_tool, result = core.execute_model_tools(response)
        self.assertTrue(has_tool)
        self.assertIn("не зарегистрирован", result)


class TestCallOllama(unittest.TestCase):
    """Тесты для вызова Ollama (без реального HTTP-запроса)."""

    @unittest.skipIf(not os.environ.get("TEST_OLLAMA"), "OLLAMA не доступен в тестовом окружении")
    def test_call_ollama(self):
        """Реальный вызов Ollama (только с флагом TEST_OLLAMA)."""
        result = core.call_ollama("Say hello", "Say hello", model_override="qwen2.5-coder:14b")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)


if __name__ == "__main__":
    unittest.main()