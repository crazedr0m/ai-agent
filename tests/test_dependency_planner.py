# -*- coding: utf-8 -*-
# tests/test_dependency_planner.py — Тесты для modules/dependency_planner.py

import unittest

from modules.dependency_planner import DependencyPlanner, sort_tasks_by_dependencies


class TestDependencyPlanner(unittest.TestCase):
    """Тесты для DependencyPlanner."""

    def setUp(self):
        self.repo_map = {
            "file_sizes": {
                "main.py": {"bytes": 100, "lines": 10},
                "utils.py": {"bytes": 200, "lines": 20},
                "models.py": {"bytes": 50, "lines": 5},
            },
            "file_summary": {
                "main.py": {
                    "lines": 10, "language": "python",
                    "functions": ["main"],
                    "classes": [],
                    "imports": 1,
                },
                "utils.py": {
                    "lines": 20, "language": "python",
                    "functions": ["hello", "world"],
                    "classes": [],
                    "imports": 0,
                },
                "models.py": {
                    "lines": 5, "language": "python",
                    "functions": [],
                    "classes": ["User"],
                    "imports": 0,
                },
            },
            "import_graph": {
                "main.py": ["utils.py"],
            },
            "call_graph": {
                "main": ["hello"],
                "hello": [],
                "world": [],
            },
        }

    def test_topological_sort_leaf_first(self):
        planner = DependencyPlanner(self.repo_map)
        ordered = planner.topological_sort()
        # utils.py и models.py — листья (от них никто не зависит)
        # Должны быть первыми
        self.assertIn("utils.py", ordered[:2])
        self.assertIn("models.py", ordered[:2])

    def test_topological_sort_main_last(self):
        planner = DependencyPlanner(self.repo_map)
        ordered = planner.topological_sort()
        # main.py зависит от utils.py → должен быть позже
        self.assertGreater(ordered.index("main.py"), ordered.index("utils.py"))

    def test_generate_tasks(self):
        planner = DependencyPlanner(self.repo_map)
        tasks = planner.generate_tasks()
        self.assertIn("tasks", tasks)
        self.assertIn("summary", tasks)
        self.assertGreater(len(tasks["tasks"]), 0)

    def test_generated_task_structure(self):
        planner = DependencyPlanner(self.repo_map)
        tasks = planner.generate_tasks()
        task = tasks["tasks"][0]
        self.assertIn("id", task)
        self.assertIn("target_file", task)
        self.assertIn("status", task)
        self.assertIn("layer", task)
        self.assertIn("effort", task)

    def test_effort_low(self):
        planner = DependencyPlanner(self.repo_map)
        self.assertEqual(planner._estimate_effort("models.py"), "low")

    def test_effort_medium(self):
        planner = DependencyPlanner(self.repo_map)
        # main.py имеет всего 10 строк
        self.assertEqual(planner._estimate_effort("main.py"), "low")

    def test_sort_tasks_by_dependencies(self):
        tasks = [
            {"id": 1, "target_file": "main.py", "status": "pending"},
            {"id": 2, "target_file": "utils.py", "status": "pending"},
        ]
        sorted_tasks = sort_tasks_by_dependencies(tasks, self.repo_map)
        # utils.py должен быть первым (его не импортирует main в графе)
        self.assertEqual(sorted_tasks[0]["target_file"], "utils.py")
        self.assertEqual(sorted_tasks[1]["target_file"], "main.py")

    def test_empty_repo_map(self):
        planner = DependencyPlanner({"file_summary": {}, "file_sizes": {},
                                       "import_graph": {}, "call_graph": {}})
        ordered = planner.topological_sort()
        self.assertEqual(ordered, [])

    def test_circular_dependency(self):
        """Планировщик не должен падать на циклических зависимостях."""
        cyclic_map = {
            "file_sizes": {"a.py": {"bytes": 10, "lines": 1},
                           "b.py": {"bytes": 10, "lines": 1}},
            "file_summary": {
                "a.py": {"lines": 1, "language": "python",
                         "functions": ["a"], "classes": [], "imports": 1},
                "b.py": {"lines": 1, "language": "python",
                         "functions": ["b"], "classes": [], "imports": 1},
            },
            "import_graph": {
                "a.py": ["b.py"],
                "b.py": ["a.py"],
            },
            "call_graph": {"a": ["b"], "b": ["a"]},
        }
        planner = DependencyPlanner(cyclic_map)
        ordered = planner.topological_sort()
        # Все файлы должны быть в результате, несмотря на цикл
        self.assertEqual(len(ordered), 2)
        self.assertIn("a.py", ordered)
        self.assertIn("b.py", ordered)


if __name__ == "__main__":
    unittest.main()