# -*- coding: utf-8 -*-
# modules/dependency_planner.py — Планирование миграции по графу зависимостей (Фаза 6.2)
#
# Вместо плоского списка задач (tasks.json) строит порядок миграции
# на основе графа зависимостей: файлы, от которых никто не зависит
# (листья), мигрируются первыми, корневые — последними.
#
# Топологическая сортировка с учётом:
#   - import_graph (статический анализ)
#   - call_graph (кто кого вызывает)
#   - Размер файла (большие файлы могут дробиться на подзадачи)
#
# Использование:
#   planner = DependencyPlanner(repo_map)
#   ordered = planner.topological_sort()
#   planner.generate_tasks() -> dict (tasks.json)

import json
from typing import Optional


class DependencyPlanner:
    """Планировщик миграции на основе графа зависимостей."""

    def __init__(
        self,
        repo_map: dict,
        project_name: str = "Миграция",
        max_tasks: int = 50,
    ):
        """
        Args:
            repo_map: результат modules.repo_map.build_repo_map()
            project_name: имя проекта (для отчёта)
            max_tasks: максимальное количество задач в плане
        """
        self.repo_map = repo_map
        self.project_name = project_name
        self.max_tasks = max_tasks
        self._file_summary = repo_map.get("file_summary", {})
        self._import_graph = repo_map.get("import_graph", {})
        self._call_graph = repo_map.get("call_graph", {})
        self._file_sizes = repo_map.get("file_sizes", {})

        # Кэш для топологической сортировки
        self._sorted_files: list[str] = []
        self._layers: list[list[str]] = []  # слои для параллельного выполнения
        self._dep_cache: dict[str, set[str]] = {}  # кэш зависимостей

    # ─────────────────────────────────────────────
    # Анализ зависимостей
    # ─────────────────────────────────────────────

    def _file_has_function(self, file_path: str, func_name: str) -> bool:
        """Проверить, определена ли функция в файле."""
        funcs = self._file_summary.get(file_path, {}).get("functions", [])
        return func_name in funcs

    def _get_dependencies(self, file_path: str) -> set[str]:
        """Вернуть множество файлов, от которых зависит file_path.

        Учитывает:
        1. Прямые импорты (import_graph)
        2. Вызовы функций из других файлов (call_graph)
        """
        if file_path in self._dep_cache:
            return self._dep_cache[file_path]

        deps: set[str] = set()

        # 1. Прямые импорты
        for imp in self._import_graph.get(file_path, []):
            deps.add(imp)

        # 2. Косвенные зависимости: если функция из file_path вызывает
        #    функцию из другого файла, добавляем тот файл
        file_funcs = self._file_summary.get(file_path, {}).get("functions", [])

        for caller, callees in self._call_graph.items():
            # caller может быть с префиксом файла или без — проверяем
            if caller in file_funcs:
                for callee in callees:
                    for rel, info in self._file_summary.items():
                        if rel == file_path:
                            continue
                        if self._file_has_function(rel, callee):
                            deps.add(rel)

        self._dep_cache[file_path] = deps
        return deps

    def _get_dependents(self, file_path: str) -> list[str]:
        """Вернуть файлы, которые зависят от file_path (обратные зависимости)."""
        dependents = []
        for rel in self._file_summary:
            if file_path in self._get_dependencies(rel):
                dependents.append(rel)
        return dependents

    # ─────────────────────────────────────────────
    # Топологическая сортировка (Kahn's algorithm)
    # ─────────────────────────────────────────────

    def topological_sort(self) -> list[str]:
        """Топологическая сортировка файлов по зависимостям.

        Returns:
            список файлов, упорядоченный от листьев (независимые) к корням.
        """
        graph: dict[str, set[str]] = {}
        for rel in self._file_summary:
            graph[rel] = self._get_dependencies(rel)

        # Строим in-degree (сколько файлов зависят от этого файла)
        in_degree: dict[str, int] = {}
        for rel in graph:
            if rel not in in_degree:
                in_degree[rel] = 0
            for dep in graph[rel]:
                if dep not in in_degree:
                    in_degree[dep] = 0
                in_degree[rel] += 1

        # Узлы без входящих зависимостей
        queue = [rel for rel, deg in in_degree.items() if deg == 0]
        sorted_files = []

        while queue:
            # Мелкие файлы — первыми
            queue.sort(key=lambda x: self._file_summary.get(x, {}).get("lines", 0))
            self._layers.append(list(queue))

            next_queue = []
            for rel in queue:
                sorted_files.append(rel)
                for dep_rel, deps in graph.items():
                    if rel in deps:
                        in_degree[dep_rel] -= 1
                        if in_degree[dep_rel] == 0:
                            next_queue.append(dep_rel)
            queue = next_queue

        # Проверка на циклы
        if len(sorted_files) != len(self._file_summary):
            remaining = set(self._file_summary) - set(sorted_files)
            sorted_files.extend(remaining)
            if remaining:
                self._layers.append(list(remaining))

        self._sorted_files = sorted_files
        return sorted_files

    # ─────────────────────────────────────────────
    # Генерация задач
    # ─────────────────────────────────────────────

    def _estimate_effort(self, file_path: str) -> str:
        """Оценить сложность миграции файла."""
        info = self._file_summary.get(file_path, {})
        lines = info.get("lines", 0)
        funcs = len(info.get("functions", []))
        classes = len(info.get("classes", []))

        if lines > 500 or funcs > 20:
            return "high"
        if lines > 100 or funcs > 5:
            return "medium"
        return "low"

    def _build_task_description(self, file_path: str, deps: list[str]) -> str:
        """Сформировать описание задачи для файла."""
        info = self._file_summary.get(file_path, {})
        language = info.get("language", "unknown")
        funcs = info.get("functions", [])
        classes = info.get("classes", [])

        parts = [f"Мигрировать файл `{file_path}` ({language}, {info.get('lines', 0)} строк)"]
        if classes:
            parts.append(f"Классы: {', '.join(classes[:5])}")
        if funcs:
            parts.append(f"Функции: {', '.join(funcs[:8])}")
        if deps:
            parts.append(f"Зависимости от: {', '.join(deps[:5])}")

        return " | ".join(parts)

    def _find_layer(self, file_path: str) -> int:
        """Найти номер слоя для файла (0 = лист, выполняется первым)."""
        for i, layer in enumerate(self._layers):
            if file_path in layer:
                return i
        return len(self._layers)

    @staticmethod
    def _count_by_effort(tasks: list, level: str) -> int:
        """Подсчитать количество задач с указанным уровнем сложности."""
        return sum(1 for t in tasks if t.get("effort") == level)

    def generate_tasks(self) -> dict:
        """Сгенерировать tasks.json на основе топологической сортировки.

        Returns:
            dict в формате tasks.json (с полями tasks, project_name, status)
        """
        if not self._sorted_files:
            self.topological_sort()

        tasks = []
        for idx, file_path in enumerate(self._sorted_files[:self.max_tasks], 1):
            deps = sorted(self._get_dependencies(file_path))
            dependents = sorted(self._get_dependents(file_path))

            task = {
                "id": idx,
                "target_file": file_path,
                "description": self._build_task_description(file_path, deps),
                "status": "pending",
                "priority": idx,
                "layer": self._find_layer(file_path),
                "effort": self._estimate_effort(file_path),
                "dependencies": deps,
                "dependents": dependents,
                "functions": self._file_summary.get(file_path, {}).get("functions", []),
                "classes": self._file_summary.get(file_path, {}).get("classes", []),
            }
            tasks.append(task)

        return {
            "project_name": self.project_name,
            "status": "in_progress",
            "tasks": tasks,
            "dependency_layers": self._layers,
            "summary": {
                "total_files": len(self._file_summary),
                "total_tasks": len(tasks),
                "layers": len(self._layers),
                "highest_effort": self._count_by_effort(tasks, "high"),
                "medium_effort": self._count_by_effort(tasks, "medium"),
                "low_effort": self._count_by_effort(tasks, "low"),
            },
        }


# ── Утилита для пересортировки существующих задач ──────────────────


def sort_tasks_by_dependencies(tasks: list[dict], repo_map: dict) -> list[dict]:
    """Отсортировать существующие задачи по зависимостям.

    Полезно, если tasks.json уже существует, но порядок не учитывает
    граф зависимостей — пересортировка без потери данных.

    Args:
        tasks: список задач из tasks.json
        repo_map: результат build_repo_map()

    Returns:
        пересортированный список задач
    """
    import_graph = repo_map.get("import_graph", {})
    file_targets = {t["target_file"]: t for t in tasks}

    # Строим граф только для существующих задач
    graph: dict[str, list[str]] = {}
    for t in tasks:
        f = t["target_file"]
        deps = [d for d in import_graph.get(f, []) if d in file_targets]
        graph[f] = deps

    # Kahn's algorithm
    in_degree: dict[str, int] = {}
    for f in graph:
        if f not in in_degree:
            in_degree[f] = 0
        for d in graph[f]:
            if d not in in_degree:
                in_degree[d] = 0
            in_degree[f] += 1

    queue = [f for f, deg in in_degree.items() if deg == 0]
    sorted_files = []
    while queue:
        queue.sort()
        f = queue.pop(0)
        sorted_files.append(f)
        for f2, deps in graph.items():
            if f in deps:
                in_degree[f2] -= 1
                if in_degree[f2] == 0:
                    queue.append(f2)

    # Добавляем файлы, не попавшие в сортировку (циклы)
    for f in file_targets:
        if f not in sorted_files:
            sorted_files.append(f)

    # Переназначаем id
    result = []
    for idx, f in enumerate(sorted_files, 1):
        t = dict(file_targets[f])
        t["id"] = idx
        t["priority"] = idx
        result.append(t)

    return result