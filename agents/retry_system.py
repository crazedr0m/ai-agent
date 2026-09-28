# -*- coding: utf-8 -*-
# agents/retry_system.py — Система восстановления после ошибок (retry with escalation)

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, Callable
import core


class RetrySystem:
    """
    Система восстановления после ошибок с эскалацией.
    
    Стратегия эскалации:
    1. Retry (повторная попытка) — до 3 раз
    2. Escalation Level 1 — повышение приоритета задачи
    3. Escalation Level 2 — изменение промптов (Critic)
    4. Escalation Level 3 — Meta-Optimizer (переписывание промптов + hot reload)
    """

    def __init__(self, manifest_path: str = "migration_manifest.json"):
        self.manifest_path = manifest_path
        self.manifest = {}
        self.shared_context_path = "shared_context.json"
        self.retry_config = {
            "max_retries": 3,
            "retry_delay": 1,  # секунды
            "escalation_levels": [
                {"level": 1, "action": "increase_priority"},
                {"level": 2, "action": "critic_review"},
                {"level": 3, "action": "meta_optimizer"}
            ]
        }
        self.load_manifest()

    def load_manifest(self):
        """Загрузка манифеста."""
        if os.path.exists(self.manifest_path):
            with open(self.manifest_path, "r", encoding="utf-8") as f:
                self.manifest = json.load(f)

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Получить статус задачи из shared_context."""
        if not os.path.exists(self.shared_context_path):
            return None
        
        with open(self.shared_context_path, "r", encoding="utf-8") as f:
            context = json.load(f)
        
        for task in context.get("tasks", []):
            if task.get("id") == task_id:
                return task
        
        return None

    def update_task_status(self, task_id: str, status: str, error: Optional[str] = None):
        """Обновить статус задачи в shared_context."""
        if not os.path.exists(self.shared_context_path):
            return
        
        with open(self.shared_context_path, "r", encoding="utf-8") as f:
            context = json.load(f)
        
        for task in context.get("tasks", []):
            if task.get("id") == task_id:
                task["status"] = status
                if error:
                    task["error"] = error
                task["retry_count"] = task.get("retry_count", 0) + 1
                break
        
        with open(self.shared_context_path, "w", encoding="utf-8") as f:
            json.dump(context, f, ensure_ascii=False, indent=2)

    def should_retry(self, task_id: str) -> bool:
        """Проверить, стоит ли повторять попытку."""
        task = self.get_task_status(task_id)
        if not task:
            return False
        
        retry_count = task.get("retry_count", 0)
        max_retries = self.retry_config["max_retries"]
        
        return retry_count < max_retries

    def escalate(self, task_id: str, level: int):
        """Эскалация задачи на указанный уровень."""
        core.console.print(f"[yellow]⚠️ Эскалация задачи {task_id} на уровень {level}[/yellow]")
        
        if level == 1:
            # Повышение приоритета
            self._increase_priority(task_id)
        elif level == 2:
            # Critic review
            self._critic_review(task_id)
        elif level == 3:
            # Meta-Optimizer
            self._meta_optimizer(task_id)

    def _increase_priority(self, task_id: str):
        """Повышение приоритета задачи."""
        core.console.print("[green]🔼 Повышение приоритета задачи[/green]")
        # Логика повышения приоритета (можно реализовать через labels в tasks.json)
        pass

    def _critic_review(self, task_id: str):
        """Critic review — анализ ошибки и предложение исправлений."""
        core.console.print("[green]🔍 Critic анализирует ошибку[/green]")
        # Вызов Critic для анализа ошибки
        pass

    def _meta_optimizer(self, task_id: str):
        """Meta-Optimizer — переписывание промптов + hot reload."""
        core.console.print("[red]🚨 Meta-Optimizer запускается![/red]")
        # Вызов Meta-Optimizer для обновления промптов
        pass


# ─────────────────────────────────────────────
# Интеграция с MigrationAgent
# ─────────────────────────────────────────────

def execute_task_with_retry(task_id: str, task_func: Callable, retry_system: RetrySystem):
    """
    Выполнение задачи с retry и эскалацией.
    
    Args:
        task_id: ID задачи
        task_func: Функция для выполнения задачи
        retry_system: Система retry
    
    Returns:
        Результат выполнения задачи или None если все попытки исчерпаны
    """
    for attempt in range(retry_system.retry_config["max_retries"] + 1):
        try:
            core.console.print(f"[blue]🔹 Попытка {attempt + 1}/{retry_system.retry_config['max_retries']} для задачи {task_id}[/blue]")
            result = task_func()
            
            # Успешное выполнение
            retry_system.update_task_status(task_id, "completed")
            core.console.print(f"[green]✅ Задача {task_id} выполнена![/green]")
            return result
            
        except Exception as e:
            error_msg = str(e)
            retry_system.update_task_status(task_id, "failed", error=error_msg)
            
            if attempt < retry_system.retry_config["max_retries"]:
                # Повторная попытка
                core.console.print(f"[yellow]⚠️ Ошибка: {error_msg}. Повторная попытка через {retry_system.retry_config['retry_delay']}с...[/yellow]")
                import time
                time.sleep(retry_system.retry_config["retry_delay"])
            else:
                # Все попытки исчерпаны — эскалация
                retry_count = attempt
                escalation_level = min(retry_count, len(retry_system.retry_config["escalation_levels"]))
                retry_system.escalate(task_id, escalation_level)
                core.console.print(f"[red]❌ Задача {task_id} не выполнена после {retry_count} попыток и эскалации[/red]")
                return None
    
    return None