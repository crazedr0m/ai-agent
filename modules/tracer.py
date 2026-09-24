# -*- coding: utf-8 -*-
# modules/tracer.py — Трейсинг (JSONL, ротация)
#
# TraceSession — менеджер сессии трейсинга, пишет шаги в JSONL
# StepTrace — структура одного шага

import json
import os
import glob
import datetime


class StepTrace:
    """Один шаг трейса: вызов LLM, вызов инструмента или системное сообщение."""

    def __init__(self, step_type: str, content: str,
                 metadata: dict = None):
        """
        step_type: 'llm_call' | 'tool_call' | 'tool_result' | 'system' | 'final'
        content: текст шага (промпт, ответ, результат инструмента)
        metadata: доп. поля (model, tool_name, duration_ms, error и т.д.)
        """
        self.step_type = step_type
        self.content = content
        self.metadata = metadata or {}
        self.timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

    def to_dict(self) -> dict:
        return {
            "type": self.step_type,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StepTrace":
        trace = cls(data["type"], data["content"], data.get("metadata", {}))
        trace.timestamp = data.get("timestamp", trace.timestamp)
        return trace


class TraceSession:
    """
    Менеджер одной сессии трейсинга.

    - Создаёт директорию traces/session_<timestamp>/
    - Пишет шаги в JSONL-файл
    - Поддерживает ротацию: удаляет старые сессии при превышении лимита

    Пример:
        session = TraceSession("migration_agent")
        session.log_step(StepTrace("llm_call", prompt))
        session.log_step(StepTrace("tool_call", "...", {"tool_name": "list_dir"}))
        session.close()
    """

    MAX_SESSIONS = 20  # Максимум сессий в traces/ при ротации
    TRACES_DIR = "traces"

    def __init__(self, agent_name: str = "unknown",
                 traces_dir: str = None,
                 max_sessions: int = None):
        self.agent_name = agent_name
        self.traces_dir = traces_dir or self.TRACES_DIR
        self.MAX_SESSIONS = max_sessions or self.MAX_SESSIONS

        # Создаём traces/ если нет
        os.makedirs(self.traces_dir, exist_ok=True)

        # Генерируем имя сессии
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_id = f"session_{timestamp}"
        self.session_dir = os.path.join(self.traces_dir, self.session_id)
        os.makedirs(self.session_dir, exist_ok=True)

        # Файл для JSONL
        self.jsonl_path = os.path.join(self.session_dir, "trace.jsonl")
        self._file = open(self.jsonl_path, "w", encoding="utf-8")
        self._closed = False

        # Метаданные сессии
        self._session_meta = {
            "session_id": self.session_id,
            "agent_name": agent_name,
            "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        }

        # Пишем заголовок сессии
        self._write_line({"type": "__session_start__", **self._session_meta})

    def log_step(self, step: StepTrace):
        """Записать один шаг в JSONL."""
        if self._closed:
            return
        record = {
            "session_id": self.session_id,
            **step.to_dict(),
        }
        self._write_line(record)

    def log_llm_call(self, prompt: str, model: str = "",
                     duration_ms: float = 0):
        """Удобный метод: лог вызова LLM."""
        meta = {}
        if model:
            meta["model"] = model
        if duration_ms:
            meta["duration_ms"] = duration_ms
        self.log_step(StepTrace("llm_call", prompt, meta))

    def log_tool_call(self, tool_name: str, args: str, result: str):
        """Удобный метод: лог вызова инструмента + результат."""
        self.log_step(StepTrace("tool_call", args,
                                {"tool_name": tool_name}))
        self.log_step(StepTrace("tool_result", result,
                                {"tool_name": tool_name}))

    def log_final(self, response: str):
        """Лог финального ответа агента."""
        self.log_step(StepTrace("final", response))

    def close(self):
        """Закрыть сессию и записать метаданные завершения."""
        if self._closed:
            return
        self._closed = True
        self._write_line({
            "type": "__session_end__",
            "session_id": self.session_id,
            "finished_at": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "steps_count": self._count_steps(),
        })
        self._file.close()
        self._rotate_sessions()

    def _write_line(self, data: dict):
        """Пишет одну JSON-строку в JSONL."""
        line = json.dumps(data, ensure_ascii=False, default=str)
        self._file.write(line + "\n")
        self._file.flush()

    def _count_steps(self) -> int:
        """Считает количество шагов в файле (кроме __session_*)."""
        count = 0
        with open(self.jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    if record.get("type", "").startswith("__session_"):
                        continue
                    count += 1
                except json.JSONDecodeError:
                    pass
        return count

    def _rotate_sessions(self):
        """Ротация: удаляет самые старые сессии если превышен лимит."""
        # Собираем все директории сессий
        pattern = os.path.join(self.traces_dir, "session_*")
        all_sessions = sorted(glob.glob(pattern))
        # glob естественно сортирует по алфавиту = по времени

        if len(all_sessions) <= self.MAX_SESSIONS:
            return

        # Сколько удалить
        to_delete = len(all_sessions) - self.MAX_SESSIONS
        for old_dir in all_sessions[:to_delete]:
            import shutil
            shutil.rmtree(old_dir, ignore_errors=True)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()