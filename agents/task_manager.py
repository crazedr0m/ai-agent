# -*- coding: utf-8 -*-
# agents/task_manager.py — Управление tasks.json + shared_context
#
# Выделен из MigrationAgent при рефакторинге (Фаза 7.1).
# Отвечает только за чтение/запись JSON-файлов состояния миграции.

import json
import os
from typing import Optional


def load_tasks(tasks_path: str = "tasks.json") -> dict:
    """Загрузить tasks.json."""
    try:
        with open(tasks_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"tasks": []}


def save_tasks(data: dict, tasks_path: str = "tasks.json"):
    """Сохранить tasks.json."""
    with open(tasks_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_shared_context(path: str = "shared_context.json") -> dict:
    """Загрузить shared_context.json. Если нет — вернуть пустой."""
    if not os.path.exists(path):
        return {"tasks": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception):
        return {"tasks": []}


def save_shared_context(context: dict, path: str = "shared_context.json"):
    """Сохранить shared_context.json."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(context, f, indent=2, ensure_ascii=False)


def update_task_status(task_id: int, status: str, reason: str = "",
                       tasks_path: str = "tasks.json"):
    """Обновить статус задачи в tasks.json."""
    data = load_tasks(tasks_path)
    for task in data.get("tasks", []):
        if task["id"] == task_id:
            task["status"] = status
            if reason:
                task["fail_reason"] = reason
            break
    save_tasks(data, tasks_path)


def load_manifest(manifest_path: str = "migration_manifest.json") -> dict:
    """Загрузить manifest.json."""
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}