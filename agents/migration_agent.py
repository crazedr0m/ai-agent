# -*- coding: utf-8 -*-
# agents/migration_agent.py — MigrationAgent(BaseAgent)
#
# Объединяет:
# - agent.py (главный цикл конвейера)
# - initializer.py (генерация плана + Meta-Optimizer)
# - modules/executor.py (SDD → TDD → Coding → Critic)

import os
import json
import sys
import core
from core import BaseAgent
from modules.parser import extract_code_from_markdown
from modules.tracer import TraceSession

MAX_REACT_STEPS = 7
MAX_RETRIES = 3
MAX_FIX_ATTEMPTS = 3


class MigrationAgent(BaseAgent):
    """
    MigrationAgent — главный агент миграции легаси-кода.

    Конвейер:
    1. scan_legacy_project() — рекурсивное сканирование
    2. generate_plan() — Global Architect с ReAct → tasks.json
    3. execute_all() — итерация по задачам: SDD → TDD → Coding → Tests → Critic
    """

    def __init__(self, manifest_path: str = "migration_manifest.json",
                 model_architect: str = "qwen3-coder:30b",
                 model_coder: str = "qwen2.5-coder:14b",
                 tracer: TraceSession = None):
        super().__init__(name="migration_agent")
        self.manifest_path = manifest_path
        self.model_architect = model_architect
        self.model_coder = model_coder
        self.manifest = {}
        self.tracer = tracer

    # ─────────────────────────────────────────────
    # run() — точка входа
    # ─────────────────────────────────────────────

    def run(self):
        """Главный цикл: загрузка манифеста → план → выполнение."""
        core.console.print("[bold green]🚀 MigrationAgent запущен[/bold green]")

        # 1. Загружаем манифест
        if not os.path.exists(self.manifest_path):
            core.console.print(f"[red]❌ Манифест {self.manifest_path} не найден.[/red]")
            sys.exit(1)

        with open(self.manifest_path, "r", encoding="utf-8") as f:
            self.manifest = json.load(f)

        # 2. Инициализируем трейсер
        if self.tracer is None:
            self.tracer = TraceSession("migration_agent")

        # 3. Генерируем план если нет tasks.json
        if not os.path.exists("tasks.json"):
            core.console.print("[yellow]📋 tasks.json не найден. Генерация плана...[/yellow]")
            success = self.generate_plan()
            if not success:
                core.console.print("[red]❌ Не удалось сгенерировать план.[/red]")
                sys.exit(1)

        # 4. Итерационный конвейер
        self.execute_all()

        core.console.print("[bold green]🎉 MigrationAgent завершил работу[/bold green]")

    # ─────────────────────────────────────────────
    # scan_legacy_project — рекурсивное сканирование
    # ─────────────────────────────────────────────

    def scan_legacy_project(self, project_path: str) -> str:
        """Рекурсивно сканирует директорию легаси-проекта."""
        if not os.path.exists(project_path):
            core.console.print(f"[red]❌ Папка '{project_path}' не найдена[/red]")
            sys.exit(1)

        project_map = []
        core.console.print(f"[yellow]📂 Сканируем {project_path}...[/yellow]")

        for root, _, files in os.walk(project_path):
            if any(ignored in root for ignored in ["venv", ".git", "__pycache__", ".pytest_cache"]):
                continue

            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, project_path)

                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        head = [f.readline().rstrip() for _ in range(50)]
                        snippet = "\n".join([line for line in head if line])
                except Exception:
                    snippet = "[Бинарный файл]"

                project_map.append(
                    f"--- ФАЙЛ: {rel_path} ---\n"
                    f"=== НАЧАЛО ===\n{snippet}\n=== КОНЕЦ ===\n"
                )

        return "\n\n".join(project_map)

    # ─────────────────────────────────────────────
    # generate_plan — ReAct-цикл с Global Architect
    # ─────────────────────────────────────────────

    def generate_plan(self) -> bool:
        """Генерирует tasks.json через ReAct-цикл с Global Architect."""
        core.console.print("[bold blue]🚀 Global Architect: генерация плана...[/bold blue]")

        manifest = self.manifest
        import core_tools  # регистрируем инструменты
        files_list = core_tools.list_dir(manifest["legacy_project_path"])

        architect_template = self.load_prompt("role_global_architect1")
        system_instruction = architect_template.format(
            manifest_info=json.dumps(manifest, ensure_ascii=False, indent=2),
            files_structure=files_list
        )

        user_request = "Начни исследование проекта с помощью инструментов или выведи финальный tasks.json."

        for attempt in range(MAX_RETRIES):
            if attempt > 0:
                core.console.print(f"[yellow]🔄 Retry #{attempt + 1}/{MAX_RETRIES}...[/yellow]")

            for step in range(MAX_REACT_STEPS):
                core.console.print(f"[yellow]🤖 Шаг {step + 1}/{MAX_REACT_STEPS}...[/yellow]")

                raw_response = self.call_llm(
                    system_instruction, user_request,
                    model_override=self.model_architect
                )
                if not raw_response:
                    core.console.print("[red]❌ Пустой ответ[/red]")
                    break

                self.tracer.log_llm_call(raw_response[:500], model=self.model_architect)

                has_tool_call, tool_result = core.execute_model_tools(raw_response)
                if has_tool_call:
                    self.tracer.log_tool_call("architect_tool", raw_response[:200], tool_result[:200])
                    user_request = (
                        f"Результат инструмента:\n{tool_result}\n"
                        "Продолжай исследование или выведи финальный ```json."
                    )
                    continue

                clean_json = extract_code_from_markdown(raw_response)
                if not clean_json:
                    core.console.print("[dim]💭 Модель ещё исследует...[/dim]")
                    user_request = (
                        "Продолжай исследование или выведи финальный ```json. "
                        "Не выводи ```json пока не готов."
                    )
                    continue

                try:
                    parsed = json.loads(clean_json)
                    if "tasks" not in parsed or not isinstance(parsed["tasks"], list):
                        raise ValueError("Нет поля 'tasks'")

                    parsed["project_name"] = manifest.get("project_name", "Миграция")
                    parsed["status"] = "in_progress"

                    with open("tasks.json", "w", encoding="utf-8") as f:
                        json.dump(parsed, f, indent=2, ensure_ascii=False)

                    core.console.print("[bold green]✨ tasks.json создан![/bold green]")
                    self.tracer.log_final("Plan generated successfully")
                    return True

                except (json.JSONDecodeError, ValueError) as e:
                    core.console.print(f"[bold red]💥 Ошибка парсинга: {e}[/bold red]")
                    if attempt < MAX_RETRIES - 1 or step < MAX_REACT_STEPS - 1:
                        user_request = (
                            f"Ошибка валидации JSON: {e}\n"
                            f"Ответ: {raw_response[:1000]}\n"
                            "Исправь JSON и выведи снова в ```json."
                        )
                        continue

                    core.console.print("[bold yellow]🔥 Все попытки исчерпаны. Meta-Optimizer...[/bold yellow]")
                    return self._meta_recovery(raw_response, e, step)

            user_request = "Начни исследование проекта с помощью инструментов или выведи финальный tasks.json."

        return False

    # ─────────────────────────────────────────────
    # execute_all — итерация по tasks.json
    # ─────────────────────────────────────────────

    def execute_all(self):
        """Итерационный конвейер: выполняет задачи из tasks.json."""
        core.console.print("[bold green]🚀 Конвейер задач запущен[/bold green]")

        while True:
            with open("tasks.json", "r", encoding="utf-8") as f:
                plan = json.load(f)

            current_task = next((t for t in plan["tasks"] if t["status"] == "pending"), None)
            if not current_task:
                core.console.print("[bold green]🎉 Все задачи выполнены![/bold green]")
                return

            current_task["status"] = "in_progress"
            with open("tasks.json", "w", encoding="utf-8") as f:
                json.dump(plan, f, indent=2, ensure_ascii=False)

            success = self._execute_single_task(current_task)
            if not success:
                core.console.print(f"[yellow]⚠️ Задача #{current_task['id']} упала[/yellow]")
                current_task["status"] = "failed"
                with open("tasks.json", "w", encoding="utf-8") as f:
                    json.dump(plan, f, indent=2, ensure_ascii=False)

    def _execute_single_task(self, task: dict) -> bool:
        """Выполняет одну задачу: SDD → TDD → Coding → Tests → Critic."""
        task_id = task["id"]
        target_file = task["target_file"]
        core.console.print(f"\n[bold cyan]🎬 [Task #{task_id}] {target_file}[/bold cyan]")

        manifest = self.manifest
        stack_str = json.dumps(manifest["target_stack"], ensure_ascii=False, indent=2)
        constraints_str = "\n- ".join(manifest["constraints"])

        # ── SDD ──
        core.console.print("[yellow]📐 SDD...[/yellow]")
        sdd_template = self.load_prompt("sdd_architect")
        sdd_system = sdd_template.format(target_stack=stack_str, constraints=constraints_str)
        sdd_user = f"Задача: {task['description']}\nЦелевой файл: {target_file}"
        sdd_doc = self.call_llm(sdd_system, sdd_user, model_override=self.model_architect)
        self.tracer.log_llm_call(sdd_doc[:300], model=self.model_architect)

        # ── TDD ──
        core.console.print("[yellow]🧪 TDD...[/yellow]")
        test_file = f"test_{os.path.basename(target_file)}"
        tdd_template = self.load_prompt("tdd_tester")
        test_system = tdd_template.format(sdd_document=sdd_doc)
        raw_test = self.call_llm(test_system, "Сгенерируй тесты.")
        test_code = extract_code_from_markdown(raw_test)
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(test_code)

        # ── Coding ──
        core.console.print("[yellow]💻 Coding...[/yellow]")
        coder_template = self.load_prompt("coder_developer")
        coder_system = coder_template.format(
            sdd_document=sdd_doc,
            test_code=test_code,
            constraints_info=constraints_str
        )
        raw_code = self.call_llm(coder_system, "Напиши код реализации.")
        target_code = extract_code_from_markdown(raw_code)
        os.makedirs(os.path.dirname(target_file), exist_ok=True)
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(target_code)

        # ── Validation + Critic ──
        for attempt in range(MAX_FIX_ATTEMPTS):
            success, test_log = core.run_isolated_tests(test_file)
            if success:
                core.console.print(f"[bold green]🎉 Задача #{task_id} выполнена![/bold green]")
                self._update_task_status(task_id, "completed")
                return True

            attempt_num = attempt + 1
            core.console.print(f"[bold red]💥 Тесты упали. Попытка {attempt_num}/{MAX_FIX_ATTEMPTS}[/bold red]")

            critic_template = self.load_prompt("critic_debugger")
            critic_system = critic_template.format(
                target_code=target_code,
                test_code=test_code,
                test_log=test_log
            )
            raw_fix = self.call_llm(critic_system, "Исправь ошибку.")
            target_code = extract_code_from_markdown(raw_fix)
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(target_code)

        # ── Meta-Optimizer (эволюция промптов) ──
        core.console.print("[red]❌ Предел попыток. Meta-Optimizer...[/red]")
        meta_system = self.load_prompt("role_critic_optimizer")
        current_coder = self.load_prompt("coder_developer")
        meta_user_template = self.load_prompt("role_critic_optimizer_user")
        meta_user = meta_user_template.format(
            current_coder_prompt=current_coder,
            target_code=target_code,
            test_log=test_log
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