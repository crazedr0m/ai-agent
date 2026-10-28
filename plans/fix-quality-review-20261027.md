# План исправлений по quality-review-20261027

> Источник: [`plans/quality-review-20261027.md`](quality-review-20261027.md)
> Принцип: маленькие партии, каждая — самостоятельно проверяемая. Сначала тесты, потом фикс.

## Порядок партий

| Партия | Тема | Пункты обзора | Риск |
|---|---|---|---|
| B0 | Страховочная сетка: характеризационные тесты агентов | P0.1 | нет |
| B1 | Целостность состояния (атомарная запись, ключи, пути, таймаут) | Q-6, Q-7, Q-9, Q-10, Q-11 | низкий |
| B2 | Корректность конвейера (слои, sandbox, тестовые файлы, параллелизм) | C-1, C-2, C-3, C-4 | средний |
| B3 | Retry/эскалация и мета-оптимизатор | C-5, C-7 | средний |
| B4 | Память | C-6 | низкий |
| B5 | Архитектура ядра и конфигурация | A-1, A-2, A-5 | высокий |
| B6 | Гигиена: мёртвый код, logging, документация | A-3, A-4, Q-1, Q-2, Q-13, D-1…D-7 | низкий |

## B0 — характеризационные тесты (до любых правок)

Файлы: `tests/test_pipeline_executor.py`, `tests/test_task_manager.py`, `tests/test_retry_system.py`, `tests/test_migration_agent.py`.

- `call_llm` подменяется `unittest.mock.MagicMock` — реальный Ollama не нужен.
- `run_isolated_tests` подменяется на детерминированный результат.
- Фиксируем текущее поведение (в т.ч. дефектное), чтобы видеть регрессии при фиксах.

## B1 — целостность состояния

1. `agents/task_manager.py`: `_atomic_write_json()` через `tempfile.NamedTemporaryFile` + `os.replace`; применить в `save_tasks`, `save_shared_context`.
2. `load_tasks`: `JSONDecodeError` → исключение `StateCorruptedError` вместо `{"tasks": []}`; вызывающий код (`MigrationAgent.run`) печатает ошибку и завершается, а не «успешно мигрирует 0 задач».
3. Нормализация ключей `shared_state.*` к `str(task_id)` при записи и чтении (убрать зависимость от fallback).
4. `PipelineExecutor`: `target_file` нормализуется (`os.path.normpath`), проверка на выход за корень проекта, `os.makedirs` только если `dirname` непустой.
5. `_core.run_isolated_tests`: `timeout=` (значение из манифеста, дефолт 300 с), `TimeoutExpired` → `(False, "timeout")`.
6. `execute_all_with_retry`: подхватывать `in_progress` задачи (после падения процесса) наравне с `pending`.

## B2 — корректность конвейера

1. C-4: выполнение по `dependency_layers` — слой за слоем, внутри слоя параллельно.
2. C-3: sandbox убрать из конвейера (решение по умолчанию) — либо `with Sandbox(...)` + `accept()` при успехе. Ошибка входа не глотается, а логируется.
3. C-2: тестовый файл в `tests/generated/task_<id>_<basename>`; `shared_context` — единый объект с `asyncio.Lock` и запись только под локом.
4. C-1: `await asyncio.to_thread(self.agent.call_llm, ...)` + `asyncio.Semaphore` (ёмкость из манифеста, дефолт 1–2).

## B3 — retry и мета-оптимизатор

1. C-5: либо реализовать эскалацию (L1 — приоритет в `tasks.json`, L2 — Critic-анализ с записью в `shared_context`, L3 — Meta-Optimizer), либо удалить и честно описать в AGENTS.md. Единый тип `task_id: int`.
2. C-7: перед записью промпта — проверка набора плейсхолдеров (`string.Formatter().parse`), удаление ` thinking…</think>`, бэкап в `prompts/.backup/`, откат при падении следующей задачи; мета-оптимизатор не на каждом провале.

## B4 — память

`core/core_tools.py`: публичный `ToolRegistry.call(name, **kwargs)`; `FractionalMemory` использует его, логирует причину отключения через `logging`.

## B5 — архитектура (выполняется ПЕРВОЙ, блокирует остальное)

### B5.0 Факты, подтверждённые кодом

| Что | Где | Следствие |
|---|---|---|
| `_core.py` исполняется дважды | [`core/__init__.py:15-19`](../core/__init__.py:15), [`core/core.py:14-17`](../core/core.py:14) | два объекта модуля, два `console`, два набора функций |
| Атрибуты копируются снимком | [`core/__init__.py:27-32`](../core/__init__.py:27) | `core.call_ollama` ≠ `core.core._root_core.call_ollama` |
| `_core` в `ZONE_MODULES` | [`modules/hot_reload.py:40`](../modules/hot_reload.py:40) | ключа нет в `sys.modules` (там `_root_core`) → reload no-op |
| `sys.path.append` в ядре | [`_core.py:19`](../_core.py:19) | проект не оформлен как пакет |
| Мёртвые константы | [`_core.py:15-16`](../_core.py:15) | `OLLAMA_URL`, `ANALYZER_MODEL` не используются |
| URL в 3 местах | [`_core.py:15`](../_core.py:15), [`modules/llm/adapter.py:24`](../modules/llm/adapter.py:24), [`modules/eval/utils.py:9`](../modules/eval/utils.py:9) | рассинхронизация |
| `.env.example` врёт | [`.env.example:7`](../.env.example:7) | `/api/generate`, а адаптер ходит в `/api/chat` |
| `python-dotenv` не читается | [`requirements.txt:3`](../requirements.txt:3) | env игнорируется |
| Тесты завязаны на `_core` | [`tests/test_core_foundation.py:22`](../tests/test_core_foundation.py:22) | 15+ `import _core` / `patch("_core.console")` |

### B5.1 Шаг 1 — единая загрузка ядра (без перемещения файла)

Новый файл `core/runtime.py` — единственное место, где `_core.py` попадает в память:

```python
# core/runtime.py
import importlib.util, os, sys

_core_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_core.py"
)
_spec = importlib.util.spec_from_file_location("_root_core", _core_path)
_root_core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_root_core)

sys.modules["_root_core"] = _root_core
sys.modules["_core"] = _root_core   # алиас: hot_reload + легаси-тесты
```

- [`core/__init__.py`](../core/__init__.py): убрать `exec_module`, взять `from .runtime import _root_core`.
- [`core/core.py`](../core/core.py): убрать `exec_module`, взять `from .runtime import _root_core`.
- [`modules/hot_reload.py`](../modules/hot_reload.py): `"_core"` → `"_root_core"` в supervised.
- Результат: один объект модуля, `patch` в одном месте виден везде, reload работает.

### B5.2 Шаг 2 — оформление пакета

`pyproject.toml`:

```toml
[project]
name = "ai-agent"
version = "1.0.0"
requires-python = ">=3.10"
dependencies = ["requests", "rich>=13.0.0", "python-dotenv", "mcp", "fastmcp", "tree-sitter"]

[project.optional-dependencies]
dev = ["coverage>=7.6.0"]

[project.scripts]
agent = "agent:main"

[tool.setuptools]
py-modules = ["agent", "core_tools", "_core", "initializer"]
packages = ["core", "agents", "modules", "modules.llm", "modules.eval", "modules.tui", "mcp_servers", "mcp_servers.code_analyzer", "mcp_servers.fetch", "mcp_servers.filesystem", "mcp_servers.fractional_memory"]
```

- `pip install -e .` → импорты работают без `sys.path`-хаков.
- Удалить `sys.path.append` из [`_core.py:19`](../_core.py:19), `sys.path.insert` из [`tests/__init__.py:10`](../tests/__init__.py:10), [`tests/test_repo_map.py:10`](../tests/test_repo_map.py:10), [`tests/test_dependency_planner.py:8`](../tests/test_dependency_planner.py:8), [`tests/test_migration_context.py:9`](../tests/test_migration_context.py:9), [`modules/tui/example.py:10`](../modules/tui/example.py:10).
- `coverage` переезжает в `[project.optional-dependencies].dev`.
- `requirements.txt` либо удаляется, либо генерируется из `pyproject.toml`.

### B5.3 Шаг 3 — единый Settings

Новый `modules/settings.py`:

```python
@dataclass(frozen=True)
class Settings:
    ollama_base_url: str      # env OLLAMA_BASE_URL, дефолт http://192.168.5.7:11434
    model_architect: str      # env ARCHITECT_MODEL
    model_coder: str          # env CODER_MODEL
    model_meta: str           # env META_MODEL
    prompts_json: Path
    tasks_json: Path
    shared_context: Path
    checkpoints_dir: Path
    traces_dir: Path
    test_timeout: int         # env TEST_TIMEOUT, дефолт 300
    max_concurrency: int      # env MAX_CONCURRENCY, дефолт 2
```

- `load_dotenv()` один раз при импорте модуля.
- Значения по умолчанию для моделей — из [`model_profiles.json`](../model_profiles.json) (`defaults`), не из литералов.
- Потребители: [`modules/llm/adapter.py`](../modules/llm/adapter.py), [`modules/eval/utils.py`](../modules/eval/utils.py), [`agents/migration_agent.py`](../agents/migration_agent.py), [`agents/pipeline_executor.py`](../agents/pipeline_executor.py), [`agent.py`](../agent.py).
- Удалить `OLLAMA_URL`/`ANALYZER_MODEL` из [`_core.py`](../_core.py:15).
- Исправить [`.env.example`](../.env.example:7): `OLLAMA_BASE_URL=http://192.168.5.7:11434` (без `/api/...`).

### B5.4 Шаг 4 (опционально, отдельной партией) — перенос файла

`_core.py` → `core/runtime.py` как обычный модуль, `exec_module` исчезает совсем.
Требует правки 15+ тестов (`import _core` → `from core import runtime`).
Делать только после того, как B5.1–B5.3 стабильны.

### B5.5 A-2 — зоны мутабельности в коде

- `modules/zones.py`: `zone_of(path) -> "kernel" | "supervised" | "autonomous"`, источник — `ZONE_MODULES` + ADR-001.
- [`modules/dev_tools.py`](../modules/dev_tools.py): `write_file`/`apply_diff` отказывают для `kernel`, требуют `confirm_action` для `supervised`.
- Мета-оптимизатор (B3) проверяет зону перед записью промпта.

### B5.6 Риски и порядок

| Риск | Митигация |
|---|---|
| `_core.py` помечен IMMUTABLE, но правки нужны | ADR-001: он `supervised` → подтверждение человека (y/n) на каждую правку |
| `pip install -e .` может конфликтовать с существующим `venv/` | `venv/` не трогаем, ставим внутрь него |
| `py-modules` с `_core` ломает `import _core` в тестах | алиас `sys.modules["_core"]` из B5.1 сохраняет совместимость |
| `core_tools.py` (корень) и `core/core_tools.py` — разные модули с похожими именами | не переименовываем в этой партии, фиксируем как долг |

Порядок внутри B5: **B5.1 → B5.3 → B5.2 → B5.5 → B5.4**.
B5.1 и B5.3 не меняют поведение и проверяются существующими тестами; B5.2 меняет способ импорта — после него прогон `unittest discover` обязателен.

## B6 — гигиена

Мёртвый код (`_execute_single_task`, коллизия `_meta_recovery`, `OLLAMA_URL`, дубли `load_prompt*`), `except Exception: pass` → `logging`, синхронизация AGENTS.md/CONTEXT.md (D-1…D-7), чистка корня.

## Критерий готовности партии

- `python -m unittest discover -s tests` — зелёный.
- Новые тесты покрывают исправленный дефект.
- Ни одна правка не трогает `venv/`.
