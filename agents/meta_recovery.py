# -*- coding: utf-8 -*-
# agents/meta_recovery.py — Meta-Optimizer: диагностика ошибок и восстановление
#
# Выделен из MigrationAgent._meta_recovery при рефакторинге (Фаза 7.1).
# Не зависит от MigrationAgent — принимает AgentInterface для call_llm / load_prompt.

import json
import core
from modules.parser import extract_code_from_markdown
from modules.settings import settings


class MetaRecovery:
    """Диагностика ошибок ReAct-цикла и автоисправление кода/промптов.

    Использует deepseek-r1:32b для анализа ошибки и генерации фикса.
    """

    def __init__(self, agent, tracer=None):
        """
        Args:
            agent: объект с методами call_llm(system, user, model_override) и load_prompt(role)
            tracer: опциональный TraceSession
        """
        self.agent = agent
        self.tracer = tracer

    def diagnose_and_fix(self, raw_response: str, error: Exception,
                         step: int) -> bool:
        """Проанализировать ошибку ReAct-шага и попытаться исправить.

        Args:
            raw_response: ответ модели, вызвавший ошибку
            error: исключение
            step: номер шага (0-based)

        Returns:
            True если фикс применён, False если не удалось
        """
        core.console.print("[bold yellow]🧠 Meta-Optimizer: диагностика...[/bold yellow]")

        try:
            parser_code = open("modules/parser.py", "r", encoding="utf-8").read()
        except Exception:
            parser_code = "[не удалось]"

        try:
            architect_prompt = self.agent.load_prompt("role_global_architect1")
        except Exception:
            architect_prompt = "[не удалось]"

        meta_system = self.agent.load_prompt("meta_recovery_system")
        meta_user_template = self.agent.load_prompt("meta_recovery_user")
        meta_user = meta_user_template.format(
            step=step + 1,
            error=error,
            raw_response=raw_response[:2000],
            parser_code=parser_code,
            architect_prompt=architect_prompt,
        )

        diagnosis_raw = self.agent.call_llm(
            meta_system, meta_user, model_override=settings.model_meta
        )

        try:
            clean = extract_code_from_markdown(diagnosis_raw)
            if not clean:
                clean = diagnosis_raw.strip()
            diag = json.loads(clean)
        except Exception as e:
            core.console.print(f"[red]❌ Meta-Optimizer ошибка: {e}[/red]")
            if self.tracer:
                from modules.tracer import StepTrace
                self.tracer.log_step(StepTrace(
                    "system", f"Meta-Optimizer failed: {e}"
                ))
            return False

        fix_type = diag.get("fix_type", "none")
        target_file = diag.get("target_file", "")
        new_content = diag.get("new_content", "")

        if fix_type == "none" or not new_content:
            core.console.print("[yellow]⚠️ Meta-Optimizer не предложил фикс[/yellow]")
            return False

        if fix_type == "code" and target_file:
            if target_file in ("core.py", "core_tools.py", "core/runtime.py"):
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
                    core.console.print(
                        "[bold yellow]🔄 Промпт обновлён. Hot reload...[/bold yellow]"
                    )
                    core.hot_reload()
                    return True
            except Exception as e:
                core.console.print(f"[red]❌ Ошибка обновления промпта: {e}[/red]")

        return False