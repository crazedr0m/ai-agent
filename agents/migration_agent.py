# -*- coding: utf-8 -*-
# agents/migration_agent.py — MigrationAgent(BaseAgent) FACADE
#
# ✅ Фаза 7: Рефакторинг. Делегирует выполнение:
#   - PipelineExecutor — конвейер SDD→TDD→Coding→Critic→Meta
#   - TaskManager — чтение/запись tasks.json и shared_context.json
#   - MetaRecovery — диагностика и автоисправление ошибок
#   - RetrySystem — retry с эскалацией
#
# Интерфейс сокращён: только run() + generate_plan().

import os
import json
import sys
import asyncio
import core
from core import BaseAgent
from modules.parser import extract_code_from_markdown
from modules.tracer import TraceSession
from modules.repo_map import build_repo_map, format_repo_map_for_llm
from modules.dependency_planner import DependencyPlanner
from modules.migration_context import CheckpointManager, LOG16Integration
from agents.retry_system import RetrySystem
from agents.pipeline_executor import PipelineExecutor
from agents.task_manager import load_tasks, save_tasks, load_manifest, update_task_status
from agents.meta_recovery import MetaRecovery

MAX_RETRIES = 3
MAX_REACT_STEPS = 10


class MigrationAgent(BaseAgent):
    """
    MigrationAgent — главный агент миграции легаси-кода (Facade).

    Конвейер:
    1. scan_legacy_project() — сканирование через repo_map
    2. generate_plan() — Global Architect / DependencyPlanner → tasks.json
    3. execute_all_with_retry() — параллельное выполнение через PipelineExecutor

    ✅ Фаза 7: внутренняя логика вынесена в подмодули.
    """

    def __init__(self, manifest_path: str = "migration_manifest.json",
                 model_architect: str = "qwen3-coder:30b",
                 model_coder: str = "qwen2.5-coder:14b",
                 tracer: TraceSession = None):
        super().__init__(name="migration_agent", max_steps=10,
                         model="qwen2.5-coder:14b")
        self.manifest_path = manifest_path
        self.model_architect = model_architect
        self.model_coder = model_coder
        self.manifest = {}
        self.tracer = tracer
        self.retry_system = RetrySystem(self.manifest_path)
        self._repo_map = None
        self.shared_context_path = "shared_context.json"

        # Регистрируем инструменты
        import core_tools  # noqa: F401

        # Чекпоинты и LOG16
        project_name = load_manifest(self.manifest_path).get("project_name", "")
        self.checkpoint = CheckpointManager(project_name)
        self.log16 = LOG16Integration(project_name)

        # Экземпляры подмодулей (заполняются при необходимости)
        self._pipeline = None
        self._meta_recovery = None

    # ─────────────────────────────────────────────
    # run() — точка входа
    # ─────────────────────────────────────────────

    def run(self):
        """Главный цикл: манифест → repo_map → план → выполнение."""
        core.console.print("[bold green]🚀 MigrationAgent запущен[/bold green]")

        if not os.path.exists(self.manifest_path):
            core.console.print(f"[red]❌ Манифест {self.manifest_path} не найден.[/red]")
            sys.exit(1)

        with open(self.manifest_path, "r", encoding="utf-8") as f:
            self.manifest = json.load(f)
        project_path = self.manifest.get("legacy_project_path", ".")

        if self.tracer is None:
            self.tracer = TraceSession("migration_agent")

        # LOG16 recall
        core.console.print("[blue]🧠 LOG16: загрузка контекста прошлых сессий...[/blue]")
        log16_context = self.log16.recall_project_context()
        if log16_context:
            core.console.print(f"[dim]📜 Воспоминания: {log16_context[:200]}...[/dim]")
            from modules.tracer import StepTrace
            self.tracer.log_step(StepTrace(
                "system", f"LOG16 recall: {log16_context[:500]}"
            ))

        # repo_map
        core.console.print("[yellow]🗺️ Строим карту репозитория через анализатор...[/yellow]")
        self._repo_map = build_repo_map(project_path)
        from modules.tracer import StepTrace
        self.tracer.log_step(StepTrace(
            "system", f"repo_map: {self._repo_map.get('summary', {})}"
        ))
        core.console.print(
            f"[green]✅ Карта: {self._repo_map['summary']['total_files']} файлов, "
            f"{self._repo_map['summary']['total_lines']} строк[/green]"
        )

        try:
            self.log16.record_project_summary(self._repo_map)
        except Exception:
            pass

        # tasks.json: resume или генерация
        if not os.path.exists("tasks.json"):
            core.console.print("[yellow]📋 tasks.json не найден. Генерация плана...[/yellow]")
            success = self.generate_plan()
            if not success:
                core.console.print("[red]❌ Не удалось сгенерировать план.[/red]")
                sys.exit(1)
        else:
            if self.checkpoint.can_resume():
                core.console.print("[green]🔄 Обнаружен чекпоинт. Возобновление...[/green]")
                cp = self.checkpoint.load_checkpoint()
                done = cp.get("summary", {}).get("completed", 0)
                total = cp.get("summary", {}).get("total", 0)
                core.console.print(f"[dim]✅ Выполнено {done}/{total} задач[/dim]")

        # Параллельный конвейер
        asyncio.run(self.execute_all_with_retry())

        # Финальная запись LOG16
        try:
            self.log16.finalize_migration(
                self.checkpoint.load_checkpoint(),
                load_tasks()
            )
        except Exception:
            pass

        # Финальный отчёт
        if os.path.exists("checkpoints"):
            report = self.checkpoint.get_progress_report(load_tasks())
            core.console.print(f"[bold]📊 {report}[/bold]")

        core.console.print("[bold green]🎉 MigrationAgent завершил работу[/bold green]")

    # ─────────────────────────────────────────────
    # scan_legacy_project
    # ─────────────────────────────────────────────

    def scan_legacy_project(self, project_path: str) -> str:
        """Сканирование через AST-анализатор (repo_map)."""
        if self._repo_map is None:
            core.console.print("[yellow]🗺️ Строим карту репозитория...[/yellow]")
            self._repo_map = build_repo_map(project_path)
        return format_repo_map_for_llm(self._repo_map)

    # ─────────────────────────────────────────────
    # generate_plan
    # ─────────────────────────────────────────────

    def generate_plan(self) -> bool:
        """Генерация tasks.json через DependencyPlanner."""
        core.console.print(
            "[bold blue]🚀 DependencyPlanner: генерация плана по графу "
            "зависимостей...[/bold blue]"
        )
        project_path = self.manifest.get("legacy_project_path", ".")
        manifest = self.manifest

        if self._repo_map is None:
            try:
                self._repo_map = build_repo_map(project_path)
            except Exception as e:
                core.console.print(
                    f"[red]❌ Ошибка repo_map: {e}. Fallback на scan_legacy_project.[/red]"
                )
                project_scan = self.scan_legacy_project(project_path)
                self._repo_map = None
        else:
            project_scan = format_repo_map_for_llm(self._repo_map)

        try:
            planner = DependencyPlanner(
                repo_map=self._repo_map,
                project_name=manifest.get("project_name", "Миграция"),
            )
            tasks = planner.generate_tasks()
        except Exception as e:
            core.console.print(
                f"[red]❌ Ошибка DependencyPlanner: {e}. Fallback на ReAct.[/red]"
            )
            return self._generate_plan_react(project_scan)

        tasks["project_name"] = manifest.get("project_name", "Миграция")
        tasks["status"] = "in_progress"
        save_tasks(tasks)

        core.console.print(
            f"[bold green]✨ tasks.json создан! {len(tasks['tasks'])} задач, "
            f"{len(tasks.get('dependency_layers', []))} слоёв[/bold green]"
        )
        from modules.tracer import StepTrace
        self.tracer.log_step(StepTrace(
            "system", f"Plan generated: {len(tasks['tasks'])} tasks"
        ))

        try:
            self.log16.record_task_completed(
                {"target_file": "PLAN", "effort": "?", "layer": 0},
                self._repo_map.get("summary") if self._repo_map else None,
            )
        except Exception:
            pass

        return True

    # ─────────────────────────────────────────────
    # _generate_plan_react (fallback)
    # ─────────────────────────────────────────────

    def _generate_plan_react(self, project_scan: str) -> bool:
        """Fallback: ReAct-цикл с Global Architect."""
        core.console.print(
            "[yellow]⚠️ Fallback: ReAct-цикл с Global Architect...[/yellow]"
        )
        manifest = self.manifest
        import core_tools  # noqa: F401

        architect_template = self.load_prompt("role_global_architect1")
        system_instruction = architect_template.format(
            manifest_info=json.dumps(manifest, ensure_ascii=False, indent=2),
            files_structure=project_scan,
        )

        user_request = (
            "Начни исследование проекта с помощью инструментов "
            "или выведи финальный ```json."
        )

        for attempt in range(MAX_RETRIES):
            if attempt > 0:
                core.console.print(
                    f"[yellow]🔄 Retry #{attempt + 1}/{MAX_RETRIES}...[/yellow]"
                )

            for step in range(MAX_REACT_STEPS):
                core.console.print(
                    f"[yellow]🤖 Шаг {step + 1}/{MAX_REACT_STEPS}...[/yellow]"
                )

                raw_resp = self.call_llm(
                    system_instruction, user_request,
                    model_override=self.model_architect
                )
                if not raw_resp:
                    core.console.print("[red]❌ Пустой ответ[/red]")
                    break

                self.tracer.log_llm_call(raw_resp[:500],
                                          model=self.model_architect)

                has_tc, tc_res = self.engine.execute_tool_call(raw_resp)
                if has_tc:
                    self.tracer.log_tool_call("architect_tool",
                                               raw_resp[:200], tc_res[:200])
                    user_request = (
                        f"Результат инструмента:\n{tc_res}\n"
                        "Продолжай исследование или выведи финальный ```json."
                    )
                    continue

                clean = extract_code_from_markdown(raw_resp)
                if not clean:
                    core.console.print("[dim]💭 Модель ещё исследует...[/dim]")
                    user_request = (
                        "Продолжай исследование или выведи финальный ```json. "
                        "Не выводи ```json пока не готов."
                    )
                    continue

                try:
                    parsed = json.loads(clean)
                    if "tasks" not in parsed or not isinstance(parsed["tasks"], list):
                        raise ValueError("Нет поля 'tasks'")
                    parsed["project_name"] = manifest.get("project_name", "Миграция")
                    parsed["status"] = "in_progress"
                    save_tasks(parsed)
                    core.console.print(
                        "[bold green]✨ tasks.json создан (fallback)![/bold green]"
                    )
                    from modules.tracer import StepTrace
                    self.tracer.log_step(StepTrace(
                        "system", "Plan generated via ReAct fallback"
                    ))
                    return True
                except (json.JSONDecodeError, ValueError) as e:
                    core.console.print(
                        f"[bold red]💥 Ошибка парсинга: {e}[/bold red]"
                    )
                    if attempt < MAX_RETRIES - 1 or step < MAX_REACT_STEPS - 1:
                        user_request = (
                            f"Ошибка валидации JSON: {e}\n"
                            f"Ответ: {raw_resp[:1000]}\n"
                            "Исправь JSON и выведи снова в ```json."
                        )
                        continue
                    core.console.print("[bold yellow]🔥 Все попытки исчерпаны.[/bold yellow]")
                    return False

            user_request = (
                "Начни исследование проекта с помощью инструментов "
                "или выведи финальный ```json."
            )

        return False

    # ─────────────────────────────────────────────
    # execute_all_with_retry — параллельный конвейер
    # ─────────────────────────────────────────────

    def _get_pipeline(self) -> PipelineExecutor:
        """Ленивая инициализация PipelineExecutor."""
        if self._pipeline is None:
            self._pipeline = PipelineExecutor(
                self,
                checkpoint=self.checkpoint,
                log16=self.log16,
                tracer=self.tracer,
                repo_map=self._repo_map,
                shared_context_path=self.shared_context_path,
                model_architect=self.model_architect,
                model_coder=self.model_coder,
            )
        return self._pipeline

    def _get_meta_recovery(self) -> MetaRecovery:
        """Ленивая инициализация MetaRecovery."""
        if self._meta_recovery is None:
            self._meta_recovery = MetaRecovery(self, tracer=self.tracer)
        return self._meta_recovery

    async def execute_all_with_retry(self):
        """Параллельный конвейер с retry и эскалацией для задач из tasks.json."""
        core.console.print(
            "[bold green]🚀 Конвейер задач запущен (параллельно + retry)[/bold green]"
        )

        while True:
            plan = load_tasks()
            pending_tasks = [t for t in plan.get("tasks", [])
                             if t.get("status") == "pending"]
            if not pending_tasks:
                core.console.print("[bold green]🎉 Все задачи выполнены![/bold green]")
                return

            for task in pending_tasks:
                task["status"] = "in_progress"
            save_tasks(plan)

            pipeline = self._get_pipeline()
            manifest = self.manifest
            stack_str = json.dumps(manifest.get("target_stack", []),
                                   ensure_ascii=False, indent=2)
            constraints_str = "\n- ".join(manifest.get("constraints", []))

            async def run_with_retry(task: dict) -> tuple:
                """Выполнить задачу через pipeline с retry и эскалацией."""
                task_id = task["id"]
                target_file = task["target_file"]
                core.console.print(
                    f"\n[bold cyan]🎬 [Task #{task_id}] {target_file}[/bold cyan]"
                )

                for attempt in range(self.retry_system.retry_config["max_retries"] + 1):
                    try:
                        _, success, error = await pipeline.execute(
                            task_id, target_file, task, manifest,
                            stack_str, constraints_str,
                        )
                        if success:
                            return task_id, True, None
                        core.console.print(
                            f"[yellow]⚠️ Попытка {attempt + 1} задачи {task_id}: "
                            f"{error[:100] if error else '?'}...[/yellow]"
                        )
                    except Exception as e:
                        core.console.print(
                            f"[red]❌ Попытка {attempt + 1} задачи {task_id}: {e}[/red]"
                        )
                        error = str(e)

                    self.retry_system.update_task_status(
                        task_id, "failed", error=str(error)
                    )

                    if attempt < self.retry_system.retry_config["max_retries"]:
                        _escalation_level = min(
                            attempt + 1,
                            len(self.retry_system.retry_config["escalation_levels"])
                        )
                        self.retry_system.escalate(task_id, _escalation_level)

                return task_id, False, str(error) if 'error' in dir() else "All retries exhausted"

            # Параллельное выполнение
            results = await asyncio.gather(
                *[run_with_retry(task) for task in pending_tasks],
                return_exceptions=True
            )

            # Обработка результатов
            for result in results:
                if isinstance(result, Exception):
                    continue
                task_id, success, error = result
                task = next((t for t in plan["tasks"] if t["id"] == task_id), None)
                if task and not success:
                    core.console.print(
                        f"[yellow]⚠️ Задача #{task_id} упала: "
                        f"{str(error or '')[:100]}...[/yellow]"
                    )
                    task["status"] = "failed"

            save_tasks(plan)

    # ─────────────────────────────────────────────
    # _execute_single_task — синхронный (DEPRECATED, оставлен для совместимости)
    # ─────────────────────────────────────────────

    def _execute_single_task(self, task: dict) -> bool:
        """Синхронное выполнение одной задачи (DEPRECATED — используйте PipelineExecutor).

        Вызов: _execute_single_task(task)
        Сохранён для совместимости, но внутри делегирует PipelineExecutor через run_until_complete.
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        manifest = self.manifest
        stack_str = json.dumps(manifest.get("target_stack", []),
                               ensure_ascii=False, indent=2)
        constraints_str = "\n- ".join(manifest.get("constraints", []))

        coro = self._get_pipeline().execute(
            task["id"], task["target_file"], task, manifest,
            stack_str, constraints_str,
        )
        _, success, _ = loop.run_until_complete(coro)
        return bool(success)

    # ─────────────────────────────────────────────
    # _meta_recovery — делегирует MetaRecovery
    # ─────────────────────────────────────────────

    def _meta_recovery(self, raw_response: str, error: Exception,
                       step: int) -> bool:
        """Диагностика ошибки ReAct-шага через MetaRecovery."""
        return self._get_meta_recovery().diagnose_and_fix(
            raw_response, error, step
        )

    # ─────────────────────────────────────────────
    # Утилиты (делегируют TaskManager)
    # ─────────────────────────────────────────────

    def _load_tasks_json(self) -> dict:
        """Загрузить tasks.json."""
        return load_tasks()

    def _update_task_status(self, task_id: int, status: str, reason: str = ""):
        """Обновить статус задачи."""
        update_task_status(task_id, status, reason=reason)