# -*- coding: utf-8 -*-
# agents/migration_agent.py — MigrationAgent(BaseAgent)
#
# ✅ Фаза 6: Интеграция репозиторной карты, графа зависимостей,
#            чекпоинтов, песочницы и LOG16-памяти.

import os
import json
import sys
import asyncio
from datetime import datetime
import core
from core import BaseAgent
from modules.parser import extract_code_from_markdown
from modules.tracer import TraceSession
from modules.repo_map import build_repo_map, format_repo_map_for_llm
from modules.dependency_planner import DependencyPlanner, sort_tasks_by_dependencies
from modules.migration_context import CheckpointManager, LOG16Integration, generate_migration_report
from modules.sandbox import Sandbox
from agents.retry_system import RetrySystem, execute_task_with_retry

MAX_RETRIES = 3
MAX_FIX_ATTEMPTS = 3


class MigrationAgent(BaseAgent):
    """
    MigrationAgent — главный агент миграции легаси-кода.

    ✅ Фаза 6: Рефакторинг больших проектов
    - 6.1: repo_map — карта репозитория на базе анализатора вместо чтения файлов
    - 6.2: DependencyPlanner — планирование по графу зависимостей
    - 6.3: CheckpointManager + Sandbox — инкрементальные коммиты, возобновление после сбоя
    - 6.4: LOG16Integration — долговременная память между сессиями

    Конвейер:
    1. scan_legacy_project() — рекурсивное сканирование (Фаза 6: через repo_map)
    2. generate_plan() — Global Architect с ReAct → tasks.json (Фаза 6: через DependencyPlanner)
    3. execute_all_with_retry() — параллельное выполнение (Фаза 6: чекпоинты, коммиты, LOG16)
    """

    def __init__(self, manifest_path: str = "migration_manifest.json",
                 model_architect: str = "qwen3-coder:30b",
                 model_coder: str = "qwen2.5-coder:14b",
                 tracer: TraceSession = None):
        super().__init__(name="migration_agent", max_steps=10, model="qwen2.5-coder:14b")
        self.manifest_path = manifest_path
        self.model_architect = model_architect
        self.model_coder = model_coder
        self.manifest = {}
        self.tracer = tracer
        self.shared_context_path = "shared_context.json"
        self.retry_system = RetrySystem(self.manifest_path)

        # ✅ Фаза 2: регистрируем инструменты при создании
        import core_tools  # noqa: F401

        # ✅ Фаза 6.3: CheckpointManager для инкрементальных чекпоинтов
        project_name = ""
        try:
            with open(self.manifest_path, "r", encoding="utf-8") as f:
                project_name = json.load(f).get("project_name", "")
        except Exception:
            pass
        self.checkpoint = CheckpointManager(project_name)

        # ✅ Фаза 6.4: LOG16Integration для долговременной памяти
        self.log16 = LOG16Integration(project_name)

        self._repo_map = None  # кеш карты репозитория

    # ─────────────────────────────────────────────
    # run() — точка входа
    # ─────────────────────────────────────────────

    def run(self):
        """Главный цикл: загрузка манифеста → repo_map → план → выполнение.

        ✅ Фаза 6:
        - 6.1: repo_map вместо scan_legacy_project
        - 6.2: DependencyPlanner для tasks.json
        - 6.3: CheckpointManager для resume
        - 6.4: LOG16 recall контекста предыдущих сессий
        """
        core.console.print("[bold green]🚀 MigrationAgent запущен[/bold green]")

        # 1. Загружаем манифест
        if not os.path.exists(self.manifest_path):
            core.console.print(f"[red]❌ Манифест {self.manifest_path} не найден.[/red]")
            sys.exit(1)

        with open(self.manifest_path, "r", encoding="utf-8") as f:
            self.manifest = json.load(f)
        project_path = self.manifest.get("legacy_project_path", ".")

        # 2. Инициализируем трейсер
        if self.tracer is None:
            self.tracer = TraceSession("migration_agent")

        # ✅ Фаза 6.4: Загружаем контекст предыдущих сессий из LOG16
        core.console.print("[blue]🧠 LOG16: загрузка контекста прошлых сессий...[/blue]")
        log16_context = self.log16.recall_project_context()
        if log16_context:
            core.console.print(f"[dim]📜 Воспоминания: {log16_context[:200]}...[/dim]")
            self.tracer.log_step(__import__("modules.tracer", fromlist=["StepTrace"]).StepTrace(
                "system", f"LOG16 recall: {log16_context[:500]}"
            ))

        # ✅ Фаза 6.1: строим карту репозитория
        core.console.print("[yellow]🗺️ Строим карту репозитория через анализатор...[/yellow]")
        self._repo_map = build_repo_map(project_path)
        self.tracer.log_step(__import__("modules.tracer", fromlist=["StepTrace"]).StepTrace(
            "system", f"repo_map: {self._repo_map.get('summary', {})}"
        ))
        core.console.print(f"[green]✅ Карта: {self._repo_map['summary']['total_files']} файлов, "
                           f"{self._repo_map['summary']['total_lines']} строк[/green]")

        # ✅ Фаза 6.4: сохраняем сводку в LOG16
        try:
            self.log16.record_project_summary(self._repo_map)
        except Exception:
            pass  # LOG16 опционален

        # 3. tasks.json: resume или генерация
        if not os.path.exists("tasks.json"):
            core.console.print("[yellow]📋 tasks.json не найден. Генерация плана...[/yellow]")
            success = self.generate_plan()
            if not success:
                core.console.print("[red]❌ Не удалось сгенерировать план.[/red]")
                sys.exit(1)
        else:
            # ✅ Фаза 6.3: проверяем возможность возобновления
            if self.checkpoint.can_resume():
                core.console.print("[green]🔄 Обнаружен чекпоинт. Возобновление...[/green]")
                cp = self.checkpoint.load_checkpoint()
                done = cp.get("summary", {}).get("completed", 0)
                total = cp.get("summary", {}).get("total", 0)
                core.console.print(f"[dim]✅ Выполнено {done}/{total} задач[/dim]")

        # 4. Параллельный конвейер с retry и эскалацией
        asyncio.run(self.execute_all_with_retry())

        # ✅ Фаза 6.4: финальная запись в LOG16
        try:
            self.log16.finalize_migration(
                self.checkpoint.load_checkpoint(),
                self._load_tasks_json()
            )
        except Exception:
            pass

        # ✅ Фаза 6.3: финальный отчёт
        if os.path.exists("checkpoints"):
            report = self.checkpoint.get_progress_report(self._load_tasks_json())
            core.console.print(f"[bold]📊 {report}[/bold]")

        core.console.print("[bold green]🎉 MigrationAgent завершил работу[/bold green]")

    # ─────────────────────────────────────────────
    # scan_legacy_project — сканирование через repo_map (Фаза 6.1)
    # ─────────────────────────────────────────────

    def scan_legacy_project(self, project_path: str) -> str:
        """Сканирует проект через AST-анализатор (repo_map) вместо чтения файлов."""
        if self._repo_map is None:
            core.console.print("[yellow]🗺️ Строим карту репозитория...[/yellow]")
            self._repo_map = build_repo_map(project_path)
        return format_repo_map_for_llm(self._repo_map)

    # ─────────────────────────────────────────────
    # generate_plan — через DependencyPlanner (Фаза 6.2)
    # ─────────────────────────────────────────────

    def generate_plan(self) -> bool:
        """Генерирует tasks.json через DependencyPlanner по графу зависимостей."""
        core.console.print("[bold blue]🚀 DependencyPlanner: генерация плана по графу зависимостей...[/bold blue]")

        project_path = self.manifest.get("legacy_project_path", ".")
        manifest = self.manifest

        # Убедимся, что repo_map построен
        if self._repo_map is None:
            try:
                self._repo_map = build_repo_map(project_path)
            except Exception as e:
                core.console.print(f"[red]❌ Ошибка repo_map: {e}. Fallback на scan_legacy_project.[/red]")
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
            core.console.print(f"[red]❌ Ошибка DependencyPlanner: {e}. Fallback на ReAct.[/red]")
            return self._generate_plan_react(project_scan)

        tasks["project_name"] = manifest.get("project_name", "Миграция")
        tasks["status"] = "in_progress"

        with open("tasks.json", "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=2, ensure_ascii=False)

        core.console.print(f"[bold green]✨ tasks.json создан! {len(tasks['tasks'])} задач, "
                           f"{len(tasks.get('dependency_layers', []))} слоёв[/bold green]")
        self.tracer.log_step(__import__("modules.tracer", fromlist=["StepTrace"]).StepTrace(
            "system", f"Plan generated: {len(tasks['tasks'])} tasks"
        ))

        # LOG16 запись
        try:
            self.log16.record_task_completed(
                {"target_file": "PLAN", "effort": "?", "layer": 0},
                self._repo_map.get("summary") if self._repo_map else None
            )
        except Exception:
            pass

        return True

    # ─────────────────────────────────────────────
    # _generate_plan_react — fallback на старый ReAct (если DependencyPlanner упал)
    # ─────────────────────────────────────────────

    def _generate_plan_react(self, project_scan: str) -> bool:
        """Fallback: ReAct-цикл с Global Architect (оригинальный generate_plan)."""
        core.console.print("[yellow]⚠️ Fallback: ReAct-цикл с Global Architect...[/yellow]")
        manifest = self.manifest
        import core_tools  # noqa: F401

        architect_template = self.load_prompt("role_global_architect1")
        system_instruction = architect_template.format(
            manifest_info=json.dumps(manifest, ensure_ascii=False, indent=2),
            files_structure=project_scan
        )

        user_request = "Начни исследование проекта с помощью инструментов или выведи финальный ```json."

        for attempt in range(MAX_RETRIES):
            if attempt > 0:
                core.console.print(f"[yellow]🔄 Retry #{attempt + 1}/{MAX_RETRIES}...[/yellow]")

            for step in range(MAX_REACT_STEPS):
                core.console.print(f"[yellow]🤖 Шаг {step + 1}/{MAX_REACT_STEPS}...[/yellow]")

                raw_resp = self.call_llm(system_instruction, user_request, model_override=self.model_architect)
                if not raw_resp:
                    core.console.print("[red]❌ Пустой ответ[/red]")
                    break

                self.tracer.log_llm_call(raw_resp[:500], model=self.model_architect)

                has_tc, tc_res = self.engine.execute_tool_call(raw_resp)
                if has_tc:
                    self.tracer.log_tool_call("architect_tool", raw_resp[:200], tc_res[:200])
                    user_request = f"Результат инструмента:\n{tc_res}\nПродолжай исследование или выведи финальный ```json."
                    continue

                clean = extract_code_from_markdown(raw_resp)
                if not clean:
                    core.console.print("[dim]💭 Модель ещё исследует...[/dim]")
                    user_request = "Продолжай исследование или выведи финальный ```json. Не выводи ```json пока не готов."
                    continue

                try:
                    parsed = json.loads(clean)
                    if "tasks" not in parsed or not isinstance(parsed["tasks"], list):
                        raise ValueError("Нет поля 'tasks'")
                    parsed["project_name"] = manifest.get("project_name", "Миграция")
                    parsed["status"] = "in_progress"
                    with open("tasks.json", "w", encoding="utf-8") as f:
                        json.dump(parsed, f, indent=2, ensure_ascii=False)
                    core.console.print("[bold green]✨ tasks.json создан (fallback)![/bold green]")
                    self.tracer.log_step(__import__("modules.tracer", fromlist=["StepTrace"]).StepTrace(
                        "system", "Plan generated via ReAct fallback"
                    ))
                    return True
                except (json.JSONDecodeError, ValueError) as e:
                    core.console.print(f"[bold red]💥 Ошибка парсинга: {e}[/bold red]")
                    if attempt < MAX_RETRIES - 1 or step < MAX_REACT_STEPS - 1:
                        user_request = f"Ошибка валидации JSON: {e}\nОтвет: {raw_resp[:1000]}\nИсправь JSON и выведи снова в ```json."
                        continue
                    core.console.print("[bold yellow]🔥 Все попытки исчерпаны.[/bold yellow]")
                    return False

            user_request = "Начни исследование проекта с помощью инструментов или выведи финальный ```json."

        return False

    # ─────────────────────────────────────────────
    # execute_all_with_retry — параллельный конвейер с retry и эскалацией
    # ─────────────────────────────────────────────

    async def _execute_single_task_async(self, task: dict) -> tuple:
        """Асинхронное выполнение одной задачи: SDD → TDD → Coding → Tests → Critic.
        
        ✅ Улучшение №3: Shared context между этапами конвейера
        ✅ Улучшение №4: Интеграция RetrySystem
        ✅ Фаза 6.3: CheckpointManager + Sandbox
        ✅ Фаза 6.4: LOG16Integration
        """
        task_id = task["id"]
        target_file = task["target_file"]
        core.console.print(f"\n[bold cyan]🎬 [Task #{task_id}] {target_file}[/bold cyan]")

        manifest = self.manifest
        stack_str = json.dumps(manifest["target_stack"], ensure_ascii=False, indent=2)
        constraints_str = "\n- ".join(manifest["constraints"])

        # ✅ Фаза 6.3: чекпоинт старта задачи
        self.checkpoint.save_checkpoint(task_id, "in_progress")

        # ✅ Фаза 6.3: Sandbox (если git-репо — оборачиваем изменения)
        _sandbox = None
        if os.path.exists(".git"):
            try:
                _sandbox = Sandbox(f"task_{task_id}_{target_file.replace('/', '_')}")
                _sandbox.__enter__()
            except Exception:
                _sandbox = None  # sandbox опционален

        try:
            result = await self._execute_task_pipeline(task_id, target_file, task, manifest,
                                                        stack_str, constraints_str)
            return result
        finally:
            if _sandbox:
                _sandbox.__exit__(None, None, None)

    def _log_checkpoint_and_log16(self, task_id: int, success: bool, target_file: str,
                                   error_msg: str = None, duration: float = 0):
        """Сохранить чекпоинт + записать в LOG16 после завершения задачи."""
        status = "completed" if success else "failed"
        details = {"duration_seconds": duration}
        if error_msg:
            details["error"] = error_msg[:500]

        self.checkpoint.save_checkpoint(task_id, status, details)

        # LOG16 запись
        try:
            self.log16.record_task_completed(
                {"target_file": target_file, "effort": "?", "layer": 0},
                self._repo_map.get("summary") if self._repo_map else None
            )
        except Exception:
            pass

    async def _execute_task_pipeline(self, task_id: int, target_file: str, task: dict,
                                      manifest: dict, stack_str: str,
                                      constraints_str: str) -> tuple:
        """Внутренний конвейер задачи (без sandbox-обёртки)."""
        start_time = datetime.now()

        # ── Загрузка shared context ──
        if os.path.exists(self.shared_context_path):
            with open(self.shared_context_path, "r", encoding="utf-8") as f:
                shared_ctx = json.load(f)
        else:
            shared_ctx = {
                "version": "1.0", "tasks": [],
                "global_context": {
                    "project_name": manifest.get("project_name", ""),
                    "target_stack": manifest.get("target_stack", []),
                    "constraints": manifest.get("constraints", [])
                },
                "shared_state": {
                    "sdd_documents": {}, "test_code": {},
                    "implementation_code": {}, "validation_results": {},
                    "iteration_count": 0, "total_tasks_completed": 0
                }
            }

        # ── SDD ──
        core.console.print("[yellow]📐 SDD...[/yellow]")
        sdd_template = self.load_prompt("sdd_architect")
        sdd_system = sdd_template.format(target_stack=stack_str, constraints=constraints_str)
        sdd_user = f"Задача: {task['description']}\nЦелевой файл: {target_file}"
        try:
            sdd_doc = self.call_llm(sdd_system, sdd_user, model_override=self.model_architect)
            self.tracer.log_llm_call(sdd_doc[:300], model=self.model_architect)
        except Exception as e:
            self._log_checkpoint_and_log16(task_id, False, target_file, f"SDD failed: {str(e)}")
            return task_id, False, f"SDD failed: {str(e)}"

        shared_ctx["shared_state"]["sdd_documents"][task_id] = {
            "document": sdd_doc, "iteration": 1,
            "timestamp": datetime.now().isoformat()
        }

        # ── TDD ──
        core.console.print("[yellow]🧪 TDD...[/yellow]")
        test_file = f"test_{os.path.basename(target_file)}"
        tdd_template = self.load_prompt("tdd_tester")
        sdd_doc_for_tdd = shared_ctx["shared_state"]["sdd_documents"].get(task_id, {}).get("document", sdd_doc)
        test_system = tdd_template.format(sdd_document=sdd_doc_for_tdd)
        try:
            raw_test = self.call_llm(test_system, "Сгенерируй тесты.")
            test_code = extract_code_from_markdown(raw_test)
        except Exception as e:
            self._log_checkpoint_and_log16(task_id, False, target_file, f"TDD failed: {str(e)}")
            return task_id, False, f"TDD failed: {str(e)}"

        with open(test_file, "w", encoding="utf-8") as f:
            f.write(test_code)
        shared_ctx["shared_state"]["test_code"][task_id] = {
            "code": test_code, "file": test_file,
            "timestamp": datetime.now().isoformat()
        }

        # ── Coding ──
        core.console.print("[yellow]💻 Coding...[/yellow]")
        coder_template = self.load_prompt("coder_developer")
        sdd_doc_for_coding = shared_ctx["shared_state"]["sdd_documents"].get(task_id, {}).get("document", sdd_doc)
        test_code_for_coding = shared_ctx["shared_state"]["test_code"].get(task_id, {}).get("code", test_code)
        coder_system = coder_template.format(
            sdd_document=sdd_doc_for_coding, test_code=test_code_for_coding,
            constraints_info=constraints_str
        )
        try:
            raw_code = self.call_llm(coder_system, "Напиши код реализации.")
            target_code = extract_code_from_markdown(raw_code)
        except Exception as e:
            self._log_checkpoint_and_log16(task_id, False, target_file, f"Coding failed: {str(e)}")
            return task_id, False, f"Coding failed: {str(e)}"

        os.makedirs(os.path.dirname(target_file), exist_ok=True)
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(target_code)
        shared_ctx["shared_state"]["implementation_code"][task_id] = {
            "code": target_code, "file": target_file,
            "timestamp": datetime.now().isoformat()
        }

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
                self._update_task_status(task_id, "completed")
                shared_ctx["shared_state"]["total_tasks_completed"] += 1
                shared_ctx["shared_state"]["iteration_count"] += 1
                with open(self.shared_context_path, "w", encoding="utf-8") as f:
                    json.dump(shared_ctx, f, indent=2, ensure_ascii=False)

                # ✅ Фаза 6.3: чекпоинт и LOG16
                elapsed = (datetime.now() - start_time).total_seconds()
                self._log_checkpoint_and_log16(task_id, True, target_file, duration=elapsed)
                return task_id, True, None

            attempt_num = attempt + 1
            core.console.print(f"[bold red]💥 Тесты упали. Попытка {attempt_num}/{MAX_FIX_ATTEMPTS}[/bold red]")

            critic_template = self.load_prompt("critic_debugger")
            critic_system = critic_template.format(
                target_code=target_code, test_code=test_code,
                test_log=test_log,
                shared_context=json.dumps(shared_ctx, indent=2)
            )
            try:
                raw_fix = self.call_llm(critic_system, "Исправь ошибку.")
                target_code = extract_code_from_markdown(raw_fix)
            except Exception as e:
                self._log_checkpoint_and_log16(task_id, False, target_file, f"Critic failed: {str(e)}")
                return task_id, False, f"Critic failed: {str(e)}"

            with open(target_file, "w", encoding="utf-8") as f:
                f.write(target_code)
            shared_ctx["shared_state"]["implementation_code"][task_id]["code"] = target_code

        # ── Meta-Optimizer ──
        core.console.print("[red]❌ Предел попыток. Meta-Optimizer...[/red]")
        meta_system = self.load_prompt("role_critic_optimizer")
        current_coder = self.load_prompt("coder_developer")
        meta_user_template = self.load_prompt("role_critic_optimizer_user")
        meta_user = meta_user_template.format(
            current_coder_prompt=current_coder, target_code=target_code,
            test_log=test_log, shared_context=json.dumps(shared_ctx, indent=2)
        )
        try:
            new_prompt = self.call_llm(meta_system, meta_user, model_override="deepseek-r1:32b")
        except Exception as e:
            self._log_checkpoint_and_log16(task_id, False, target_file, f"Meta-Optimizer failed: {str(e)}")
            return task_id, False, f"Meta-Optimizer failed: {str(e)}"

        if core.update_prompt_in_file("coder_developer", new_prompt):
            core.console.print("[yellow]🔄 Промпт обновлён. Hot reload...[/yellow]")
            core.hot_reload()

        self._update_task_status(task_id, "failed", reason=test_log)
        self._log_checkpoint_and_log16(task_id, False, target_file, test_log)
        return task_id, False, test_log

    async def execute_all_with_retry(self):
        """Параллельный конвейер с retry и эскалацией для задач из tasks.json.
        
        ✅ Улучшение №4: Интеграция RetrySystem
        - Параллельное выполнение через asyncio.gather()
        - Retry с эскалацией при ошибках
        - Shared context между этапами конвейера
        """
        core.console.print("[bold green]🚀 Конвейер задач запущен (параллельно + retry)[/bold green]")

        while True:
            with open("tasks.json", "r", encoding="utf-8") as f:
                plan = json.load(f)

            # Найти pending задачи
            pending_tasks = [t for t in plan["tasks"] if t["status"] == "pending"]
            if not pending_tasks:
                core.console.print("[bold green]🎉 Все задачи выполнены![/bold green]")
                return

            # Обновить статус pending задач
            for task in pending_tasks:
                task["status"] = "in_progress"
            with open("tasks.json", "w", encoding="utf-8") as f:
                json.dump(plan, f, indent=2, ensure_ascii=False)

            # ✅ Улучшение №4: Выполнение задач с retry и эскалацией
            async def execute_task_with_retry(task):
                task_id = task["id"]
                try:
                    success, error = await asyncio.to_thread(
                        self._execute_single_task_async, task
                    )
                    return task_id, success, error
                except Exception as e:
                    core.console.print(f"[red]❌ Неожиданная ошибка в задаче {task_id}: {e}[/red]")
                    return task_id, False, str(e)

            # Параллельное выполнение pending задач
            results = await asyncio.gather(
                *[execute_task_with_retry(task) for task in pending_tasks],
                return_exceptions=True
            )

            # Обработка результатов
            for i, (task_id, success, error) in enumerate(results):
                if isinstance(error, Exception):
                    error = str(error)
                
                task = next((t for t in plan["tasks"] if t["id"] == task_id), None)
                if task:
                    if not success:
                        core.console.print(f"[yellow]⚠️ Задача #{task_id} упала: {error[:100]}...[/yellow]")
                        task["status"] = "failed"

            # Сохранить результаты в shared_context
            with open(self.shared_context_path, "r", encoding="utf-8") as f:
                shared_ctx = json.load(f)
            
            for i, (task_id, success, error) in enumerate(results):
                if isinstance(error, Exception):
                    error = str(error)
                
                # Обновляем статус в shared_context
                for task_data in shared_ctx.get("tasks", []):
                    if task_data.get("id") == task_id:
                        task_data["status"] = "failed" if not success else "completed"
                        if error:
                            task_data["error"] = error[:500]

            with open(self.shared_context_path, "w", encoding="utf-8") as f:
                json.dump(shared_ctx, f, indent=2, ensure_ascii=False)

    def _execute_single_task(self, task: dict) -> bool:
        """Выполняет одну задачу: SDD → TDD → Coding → Tests → Critic.
        
        ✅ Улучшение №3: Shared context между этапами конвейера
        Все данные сохраняются в shared_context.json и передаются между шагами.
        """
        task_id = task["id"]
        target_file = task["target_file"]
        core.console.print(f"\n[bold cyan]🎬 [Task #{task_id}] {target_file}[/bold cyan]")

        manifest = self.manifest
        stack_str = json.dumps(manifest["target_stack"], ensure_ascii=False, indent=2)
        constraints_str = "\n- ".join(manifest["constraints"])

        # ── Загрузка shared context ──
        if os.path.exists(self.shared_context_path):
            with open(self.shared_context_path, "r", encoding="utf-8") as f:
                shared_ctx = json.load(f)
        else:
            shared_ctx = {
                "version": "1.0",
                "tasks": [],
                "global_context": {
                    "project_name": manifest.get("project_name", ""),
                    "target_stack": manifest.get("target_stack", []),
                    "constraints": manifest.get("constraints", [])
                },
                "shared_state": {
                    "sdd_documents": {},
                    "test_code": {},
                    "implementation_code": {},
                    "validation_results": {},
                    "iteration_count": 0,
                    "total_tasks_completed": 0
                }
            }

        # ── SDD ──
        core.console.print("[yellow]📐 SDD...[/yellow]")
        sdd_template = self.load_prompt("sdd_architect")
        sdd_system = sdd_template.format(target_stack=stack_str, constraints=constraints_str)
        sdd_user = f"Задача: {task['description']}\nЦелевой файл: {target_file}"
        sdd_doc = self.call_llm(sdd_system, sdd_user, model_override=self.model_architect)
        self.tracer.log_llm_call(sdd_doc[:300], model=self.model_architect)

        # ✅ Сохраняем SDD в shared context
        shared_ctx["shared_state"]["sdd_documents"][task_id] = {
            "document": sdd_doc,
            "iteration": 1,
            "timestamp": datetime.now().isoformat()
        }

        # ── TDD ──
        core.console.print("[yellow]🧪 TDD...[/yellow]")
        test_file = f"test_{os.path.basename(target_file)}"
        tdd_template = self.load_prompt("tdd_tester")
        
        # ✅ Передаём SDD из shared context в промпт TDD
        sdd_doc_for_tdd = shared_ctx["shared_state"]["sdd_documents"].get(task_id, {}).get("document", sdd_doc)
        test_system = tdd_template.format(sdd_document=sdd_doc_for_tdd)
        raw_test = self.call_llm(test_system, "Сгенерируй тесты.")
        test_code = extract_code_from_markdown(raw_test)
        
        # ✅ Сохраняем тесты в shared context
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(test_code)
        
        shared_ctx["shared_state"]["test_code"][task_id] = {
            "code": test_code,
            "file": test_file,
            "timestamp": datetime.now().isoformat()
        }

        # ── Coding ──
        core.console.print("[yellow]💻 Coding...[/yellow]")
        coder_template = self.load_prompt("coder_developer")
        
        # ✅ Передаём SDD и тесты из shared context в промпт Coding
        sdd_doc_for_coding = shared_ctx["shared_state"]["sdd_documents"].get(task_id, {}).get("document", sdd_doc)
        test_code_for_coding = shared_ctx["shared_state"]["test_code"].get(task_id, {}).get("code", test_code)
        
        coder_system = coder_template.format(
            sdd_document=sdd_doc_for_coding,
            test_code=test_code_for_coding,
            constraints_info=constraints_str
        )
        raw_code = self.call_llm(coder_system, "Напиши код реализации.")
        target_code = extract_code_from_markdown(raw_code)
        
        # ✅ Сохраняем реализацию в shared context
        os.makedirs(os.path.dirname(target_file), exist_ok=True)
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(target_code)
        
        shared_ctx["shared_state"]["implementation_code"][task_id] = {
            "code": target_code,
            "file": target_file,
            "timestamp": datetime.now().isoformat()
        }

        # ── Validation + Critic ──
        for attempt in range(MAX_FIX_ATTEMPTS):
            success, test_log = core.run_isolated_tests(test_file)
            
            # ✅ Сохраняем результаты валидации в shared context
            shared_ctx["shared_state"]["validation_results"][task_id] = {
                "attempt": attempt + 1,
                "success": success,
                "test_log": test_log if not success else None,
                "timestamp": datetime.now().isoformat()
            }

            if success:
                core.console.print(f"[bold green]🎉 Задача #{task_id} выполнена![/bold green]")
                self._update_task_status(task_id, "completed")
                
                # ✅ Обновляем глобальный счётчик
                shared_ctx["shared_state"]["total_tasks_completed"] += 1
                shared_ctx["shared_state"]["iteration_count"] += 1
                
                # ✅ Сохраняем updated context
                with open(self.shared_context_path, "w", encoding="utf-8") as f:
                    json.dump(shared_ctx, f, indent=2, ensure_ascii=False)
                
                return True

            attempt_num = attempt + 1
            core.console.print(f"[bold red]💥 Тесты упали. Попытка {attempt_num}/{MAX_FIX_ATTEMPTS}[/bold red]")

            critic_template = self.load_prompt("critic_debugger")
            
            # ✅ Передаём весь контекст в промпт Critic
            critic_system = critic_template.format(
                target_code=target_code,
                test_code=test_code,
                test_log=test_log,
                shared_context=json.dumps(shared_ctx, indent=2)  # ✅ Добавляем shared context
            )
            raw_fix = self.call_llm(critic_system, "Исправь ошибку.")
            target_code = extract_code_from_markdown(raw_fix)
            
            # ✅ Обновляем код в shared context
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(target_code)
            
            shared_ctx["shared_state"]["implementation_code"][task_id]["code"] = target_code

        # ── Meta-Optimizer (эволюция промптов) ──
        core.console.print("[red]❌ Предел попыток. Meta-Optimizer...[/red]")
        meta_system = self.load_prompt("role_critic_optimizer")
        current_coder = self.load_prompt("coder_developer")
        meta_user_template = self.load_prompt("role_critic_optimizer_user")
        
        # ✅ Передаём shared context в Meta-Optimizer
        meta_user = meta_user_template.format(
            current_coder_prompt=current_coder,
            target_code=target_code,
            test_log=test_log,
            shared_context=json.dumps(shared_ctx, indent=2)  # ✅ Добавляем shared context
        )
        new_prompt = self.call_llm(meta_system, meta_user, model_override="deepseek-r1:32b")
        
        if core.update_prompt_in_file("coder_developer", new_prompt):
            core.console.print("[yellow]🔄 Промпт обновлён. Hot reload...[/yellow]")
            core.hot_reload()

        self._update_task_status(task_id, "failed", reason=test_log)
        return False

    # ─────────────────────────────────────────────
    # Meta-Recovery (из initializer.py)
    # ─────────────────────────────────────────────

    def _meta_recovery(self, raw_response: str, error: Exception, step: int) -> bool:
        """Meta-Optimizer: диагностика ошибки, фикс кода или промпта."""
        core.console.print("[bold yellow]🧠 Meta-Optimizer: диагностика...[/bold yellow]")

        try:
            parser_code = open("modules/parser.py", "r", encoding="utf-8").read()
        except Exception:
            parser_code = "[не удалось]"

        try:
            architect_prompt = self.load_prompt("role_global_architect1")
        except Exception:
            architect_prompt = "[не удалось]"

        meta_system = self.load_prompt("meta_recovery_system")
        meta_user_template = self.load_prompt("meta_recovery_user")
        meta_user = meta_user_template.format(
            step=step + 1,
            error=error,
            raw_response=raw_response[:2000],
            parser_code=parser_code,
            architect_prompt=architect_prompt
        )

        diagnosis_raw = self.call_llm(meta_system, meta_user, model_override="deepseek-r1:32b")

        try:
            clean = extract_code_from_markdown(diagnosis_raw)
            if not clean:
                clean = diagnosis_raw.strip()
            diag = json.loads(clean)
        except Exception as e:
            core.console.print(f"[red]❌ Meta-Optimizer ошибка: {e}[/red]")
            self.tracer.log_step(__import__("modules").tracer.StepTrace("system",
                f"Meta-Optimizer failed: {e}"))
            return False

        fix_type = diag.get("fix_type", "none")
        target_file = diag.get("target_file", "")
        new_content = diag.get("new_content", "")

        if fix_type == "none" or not new_content:
            core.console.print("[yellow]⚠️ Meta-Optimizer не предложил фикс[/yellow]")
            return False

        if fix_type == "code" and target_file:
            if target_file in ("core.py", "core_tools.py", "_core.py"):
                core.console.print(f"[red]🚫 Заблокировано изменение {target_file}[/red]")
                return False
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(new_content)
            core.console.print(f"[bold green]✅ {target_file} исправлен[/bold green]")
            core.hot_reload()
            return True

        if fix_type == "prompt" and target_file:
            try:
                role = target_file.replace("prompts/", "").replace(".txt", "")
                if core.update_prompt_in_file(role, new_content):
                    core.console.print("[bold yellow]🔄 Промпт обновлён. Hot reload...[/bold yellow]")
                    core.hot_reload()
                    return True
            except Exception as e:
                core.console.print(f"[red]❌ Ошибка обновления промпта: {e}[/red]")

        return False

    # ─────────────────────────────────────────────
    # Утилиты
    # ─────────────────────────────────────────────

    def _load_tasks_json(self) -> dict:
        """Загрузить tasks.json."""
        try:
            with open("tasks.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"tasks": []}

    def _update_task_status(self, task_id: int, status: str, reason: str = ""):
        with open("tasks.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        for task in data["tasks"]:
            if task["id"] == task_id:
                task["status"] = status
                if reason:
                    task["fail_reason"] = reason
                break
        with open("tasks.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)