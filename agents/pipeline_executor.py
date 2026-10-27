# -*- coding: utf-8 -*-
# agents/pipeline_executor.py — Конвейер выполнения задачи (SDD → TDD → Coding → Critic → Meta)
#
# Выделен из MigrationAgent._execute_task_pipeline при рефакторинге (Фаза 7.1).
# Не зависит от MigrationAgent — принимает BaseAgent ссылку для call_llm / load_prompt.

import json
import os
import asyncio
from datetime import datetime

import core
from core import BaseAgent
from modules.parser import extract_code_from_markdown
from modules.sandbox import Sandbox

MAX_FIX_ATTEMPTS = 3


class PipelineExecutor:
    """
    Конвейер выполнения одной задачи миграции.

    SDD → TDD → Coding → Validation → Critic (до MAX_FIX_ATTEMPTS) → Meta-Optimizer.

    Interface (один публичный метод):
        async execute(task_id, target_file, task, manifest, stack_str, constraints_str)
            -> tuple[bool, str | None]

    Внутренние зависимости (передаются через constructor):
        agent: BaseAgent        — для call_llm() / load_prompt()
        checkpoint              — CheckpointManager
        log16                   — LOG16Integration
        tracer                  — TraceSession
        repo_map                — карта репозитория (опционально)
        shared_context_path     — путь к shared_context.json
        model_architect         — модель для SDD
        model_coder             — модель для Coding
    """

    def __init__(self, agent: BaseAgent, *,
                 checkpoint=None, log16=None, tracer=None, repo_map=None,
                 shared_context_path: str = "shared_context.json",
                 model_architect: str = "qwen3-coder:30b",
                 model_coder: str = "qwen2.5-coder:14b"):
        self.agent = agent
        self.checkpoint = checkpoint
        self.log16 = log16
        self.tracer = tracer
        self.repo_map = repo_map
        self.shared_context_path = shared_context_path
        self.model_architect = model_architect
        self.model_coder = model_coder

    # ─────────────────────────────────────────────
    # Публичный метод
    # ─────────────────────────────────────────────

    async def execute(self, task_id: int, target_file: str, task: dict,
                      manifest: dict, stack_str: str, constraints_str: str) -> tuple:
        """Асинхронное выполнение задачи с sandbox-обёрткой и чекпоинтами.

        Returns:
            (task_id, success: bool, error: str | None)
        """
        # Checkpoint старта
        if self.checkpoint:
            self.checkpoint.save_checkpoint(task_id, "in_progress")

        # Sandbox
        _sandbox = None
        if os.path.exists(".git"):
            try:
                _sandbox = Sandbox(f"task_{task_id}_{target_file.replace('/', '_')}")
                _sandbox.__enter__()
            except Exception:
                _sandbox = None

        try:
            result = await self._run_pipeline(
                task_id, target_file, task, manifest, stack_str, constraints_str
            )
            return result
        finally:
            if _sandbox:
                _sandbox.__exit__(None, None, None)

    # ─────────────────────────────────────────────
    # Внутренний конвейер (без sandbox)
    # ─────────────────────────────────────────────

    async def _run_pipeline(self, task_id: int, target_file: str, task: dict,
                            manifest: dict, stack_str: str,
                            constraints_str: str) -> tuple:
        """Ядро: SDD → TDD → Coding → Critic → Meta."""
        start_time = datetime.now()
        shared_ctx = self._load_or_init_shared_context(manifest)
        sdd_doc, test_code, target_code = "", "", ""

        # ── SDD ──
        core.console.print("[yellow]📐 SDD...[/yellow]")
        sdd_template = self.agent.load_prompt("sdd_architect")
        sdd_system = sdd_template.format(
            target_stack=stack_str, constraints=constraints_str
        )
        sdd_user = f"Задача: {task['description']}\nЦелевой файл: {target_file}"
        try:
            sdd_doc = self.agent.call_llm(
                sdd_system, sdd_user, model_override=self.model_architect
            )
            if self.tracer:
                self.tracer.log_llm_call(sdd_doc[:300], model=self.model_architect)
        except Exception as e:
            self._log_end(task_id, False, target_file, f"SDD failed: {str(e)}", start_time)
            return task_id, False, f"SDD failed: {str(e)}"

        self._save_to_shared(shared_ctx, task_id, "sdd_documents", {
            "document": sdd_doc, "iteration": 1,
            "timestamp": datetime.now().isoformat()
        })

        # ── TDD ──
        core.console.print("[yellow]🧪 TDD...[/yellow]")
        test_file = f"test_{os.path.basename(target_file)}"
        tdd_template = self.agent.load_prompt("tdd_tester")
        tdd_sdd = shared_ctx["shared_state"]["sdd_documents"].get(task_id, {}).get("document", sdd_doc)
        test_system = tdd_template.format(sdd_document=tdd_sdd)
        try:
            raw_test = self.agent.call_llm(test_system, "Сгенерируй тесты.")
            test_code = extract_code_from_markdown(raw_test)
        except Exception as e:
            self._log_end(task_id, False, target_file, f"TDD failed: {str(e)}", start_time)
            return task_id, False, f"TDD failed: {str(e)}"

        with open(test_file, "w", encoding="utf-8") as f:
            f.write(test_code)
        self._save_to_shared(shared_ctx, task_id, "test_code", {
            "code": test_code, "file": test_file,
            "timestamp": datetime.now().isoformat()
        })

        # ── Coding ──
        core.console.print("[yellow]💻 Coding...[/yellow]")
        coder_template = self.agent.load_prompt("coder_developer")
        coder_sdd = shared_ctx["shared_state"]["sdd_documents"].get(task_id, {}).get("document", sdd_doc)
        coder_tests = shared_ctx["shared_state"]["test_code"].get(task_id, {}).get("code", test_code)
        coder_system = coder_template.format(
            sdd_document=coder_sdd, test_code=coder_tests,
            constraints_info=constraints_str
        )
        try:
            raw_code = self.agent.call_llm(coder_system, "Напиши код реализации.")
            target_code = extract_code_from_markdown(raw_code)
        except Exception as e:
            self._log_end(task_id, False, target_file, f"Coding failed: {str(e)}", start_time)
            return task_id, False, f"Coding failed: {str(e)}"

        os.makedirs(os.path.dirname(target_file), exist_ok=True)
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(target_code)
        self._save_to_shared(shared_ctx, task_id, "implementation_code", {
            "code": target_code, "file": target_file,
            "timestamp": datetime.now().isoformat()
        })

        # ── Validation + Critic ──
        for attempt in range(MAX_FIX_ATTEMPTS):
            success, test_log = core.run_isolated_tests(test_file)
            shared_ctx["shared_state"]["validation_results"][task_id] = {
                "attempt": attempt + 1, "success": success,
                "test_log": test_log if not success else None,
                "timestamp": datetime.now().isoformat()
            }

            if success:
                core.console.print(f"[bold green]🎉 Задача #{task_id} выполнена![/bold green]")
                shared_ctx["shared_state"]["total_tasks_completed"] += 1
                shared_ctx["shared_state"]["iteration_count"] += 1
                self._save_shared_context(shared_ctx)
                elapsed = (datetime.now() - start_time).total_seconds()
                self._log_end(task_id, True, target_file, duration=elapsed)
                return task_id, True, None

            attempt_num = attempt + 1
            core.console.print(
                f"[bold red]💥 Тесты упали. Попытка {attempt_num}/{MAX_FIX_ATTEMPTS}[/bold red]"
            )

            critic_template = self.agent.load_prompt("critic_debugger")
            critic_system = critic_template.format(
                target_code=target_code, test_code=test_code,
                test_log=test_log,
                shared_context=json.dumps(shared_ctx, indent=2)
            )
            try:
                raw_fix = self.agent.call_llm(critic_system, "Исправь ошибку.")
                target_code = extract_code_from_markdown(raw_fix)
            except Exception as e:
                self._log_end(task_id, False, target_file,
                              f"Critic failed: {str(e)}", start_time)
                return task_id, False, f"Critic failed: {str(e)}"

            with open(target_file, "w", encoding="utf-8") as f:
                f.write(target_code)
            shared_ctx["shared_state"]["implementation_code"][task_id]["code"] = target_code

        # ── Meta-Optimizer ──
        core.console.print("[red]❌ Предел попыток. Meta-Optimizer...[/red]")
        meta_system = self.agent.load_prompt("role_critic_optimizer")
        current_coder = self.agent.load_prompt("coder_developer")
        meta_user_template = self.agent.load_prompt("role_critic_optimizer_user")
        meta_user = meta_user_template.format(
            current_coder_prompt=current_coder,
            target_code=target_code, test_log=test_log,
            shared_context=json.dumps(shared_ctx, indent=2)
        )
        try:
            new_prompt = self.agent.call_llm(
                meta_system, meta_user, model_override="deepseek-r1:32b"
            )
        except Exception as e:
            self._log_end(task_id, False, target_file,
                          f"Meta-Optimizer failed: {str(e)}", start_time)
            return task_id, False, f"Meta-Optimizer failed: {str(e)}"

        if core.update_prompt_in_file("coder_developer", new_prompt):
            core.console.print("[yellow]🔄 Промпт обновлён. Hot reload...[/yellow]")
            core.hot_reload()

        self._log_end(task_id, False, target_file, test_log, start_time)
        return task_id, False, test_log

    # ─────────────────────────────────────────────
    # Утилиты
    # ─────────────────────────────────────────────

    def _load_or_init_shared_context(self, manifest: dict) -> dict:
        """Загрузить shared_context.json или создать новый."""
        if os.path.exists(self.shared_context_path):
            with open(self.shared_context_path, "r", encoding="utf-8") as f:
                return json.load(f)

        return {
            "version": "1.0", "tasks": [],
            "global_context": {
                "project_name": manifest.get("project_name", ""),
                "target_stack": manifest.get("target_stack", []),
                "constraints": manifest.get("constraints", []),
            },
            "shared_state": {
                "sdd_documents": {}, "test_code": {},
                "implementation_code": {}, "validation_results": {},
                "iteration_count": 0, "total_tasks_completed": 0,
            },
        }

    def _log_end(self, task_id: int, success: bool, target_file: str,
                 error_msg: str = None, start_time: datetime = None):
        """Сохранить чекпоинт + LOG16 после завершения задачи."""
        if self.checkpoint:
            status = "completed" if success else "failed"
            details = {}
            if start_time:
                details["duration_seconds"] = (datetime.now() - start_time).total_seconds()
            if error_msg:
                details["error"] = error_msg[:500]
            self.checkpoint.save_checkpoint(task_id, status, details)

        if self.log16:
            try:
                self.log16.record_task_completed(
                    {"target_file": target_file, "effort": "?", "layer": 0},
                    self.repo_map.get("summary") if self.repo_map else None,
                )
            except Exception:
                pass

    def _save_to_shared(self, ctx: dict, task_id: int, key: str, value: dict):
        """Записать данные в shared_context под task_id."""
        ctx["shared_state"].setdefault(key, {})[task_id] = value
        self._save_shared_context(ctx)

    def _save_shared_context(self, ctx: dict):
        """Сохранить shared_context.json."""
        with open(self.shared_context_path, "w", encoding="utf-8") as f:
            json.dump(ctx, f, indent=2, ensure_ascii=False)