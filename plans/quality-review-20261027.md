# Оценка качества архитектуры и кода — ai-agent

> **Дата:** 2026-10-27
> **Метод:** статическое чтение кода + grep. Тесты и сам конвейер **не запускались**: всё, что ниже помечено «по коду», проверено чтением, а не исполнением.
> **Охват (прочитано целиком или в основной части):** [`_core.py`](../_core.py), [`core/`](../core/), [`agent.py`](../agent.py), [`agents/`](../agents/) (migration, pipeline_executor, task_manager, retry_system), [`modules/sandbox.py`](../modules/sandbox.py), [`modules/hot_reload.py`](../modules/hot_reload.py), [`modules/dev_tools.py`](../modules/dev_tools.py), [`modules/log16_integration.py`](../modules/log16_integration.py), [`core_tools.py`](../core_tools.py).
> **Не охвачено глубоко:** `modules/tui/`, `modules/eval/`, `mcp_servers/*` (кроме grep-проверок), `tool_parser.py`, `repo_map.py`, `dependency_planner.py`. Оценки по ним — только по данным [`test-coverage-analysis.md`](test-coverage-analysis.md).

---

## 1. Итоговая оценка

| Область | Оценка | Комментарий |
|---|---|---|
| Идея слоёв (core → modules → prompts) | 7/10 | Чёткая, есть ADR-001 с зонами мутабельности |
| Реализация границ слоёв | 4/10 | Ядро грузится дважды, зоны не проверяются кодом, 3 источника правды |
| Корректность конвейера миграции | 3/10 | Несколько дефектов, из-за которых заявленное поведение не работает |
| Чистота кода / дублирование | 5/10 | Есть фасады и декомпозиция (Фаза 7), но остались дубли и мёртвый код |
| Обработка ошибок и наблюдаемость | 4/10 | Много `except Exception: pass`, нет `logging` |
| Безопасность исполнения | 5/10 | `run_command` под подтверждением, но нет валидации путей и таймаутов тестов |
| Тестируемость и покрытие | 5/10 | 64% в целом, **агенты 0%** — именно там основные баги |
| Документация | 4/10 | Много, но расходится с кодом (см. D-1…D-4) |

**Главный вывод:** модульная декомпозиция (PipelineExecutor / TaskManager / MetaRecovery) сделана, но **не доведена до рабочего состояния**. Самые рискованные дефекты сидят ровно в непокрытом тестами коде (`agents/*`).

---

## 2. Критичные дефекты (ломают заявленное поведение)

### C-1. «Параллельное» выполнение на деле последовательное
- [`pipeline_executor.py:108`](../agents/pipeline_executor.py:108), [`:129`](../agents/pipeline_executor.py:129), [`:152`](../agents/pipeline_executor.py:152) — `self.agent.call_llm(...)` вызывается синхронно внутри `async def`; `requests` блокирует event loop.
- `asyncio.gather` в [`migration_agent.py:411`](../agents/migration_agent.py:411) поэтому не даёт параллелизма. [`AGENTS.md`](../AGENTS.md) утверждает «через `asyncio.to_thread()`» — в коде этого нет.
- Fix: `await asyncio.to_thread(self.agent.call_llm, ...)` + ограничение `asyncio.Semaphore` под ёмкость Ollama.

### C-2. Параллельные задачи гонятся за общими ресурсами (при исправлении C-1 станет критичным)
- `shared_context.json`: каждая задача грузит **свою копию** ([`pipeline_executor.py:97`](../agents/pipeline_executor.py:97)) и перезаписывает файл целиком ([`:283-286`](../agents/pipeline_executor.py:283)) → lost update.
- Файл тестов `test_<basename>` пишется в корень ([`:124`](../agents/pipeline_executor.py:124)) → коллизии при одинаковых basename в разных каталогах.
- `Sandbox` делает `git checkout -b` в одном рабочем каталоге ([`sandbox.py:125`](../modules/sandbox.py:125)) — параллельные задачи переключают ветки друг под другом, плюс `__enter__` требует чистое дерево, а соседняя задача его уже загрязнила.

### C-3. Sandbox в конвейере фактически бесполезен
- [`pipeline_executor.py:72-86`](../agents/pipeline_executor.py:72): sandbox входит в контекст, но `accept()` никогда не вызывается → при выходе ветка удаляется ([`sandbox.py:142-148`](../modules/sandbox.py:142)), а файлы остаются неотслеживаемыми в рабочем дереве.
- Ошибка входа глотается `except Exception: _sandbox = None` — задача молча идёт без изоляции.
- `__enter__/__exit__` вызываются вручную вместо `with`.

### C-4. Зависимости между задачами игнорируются
- `DependencyPlanner` строит слои (`dependency_layers`), но `execute_all_with_retry` берёт **все** `pending` разом ([`migration_agent.py:355-363`](../agents/migration_agent.py:355)). Слой N+1 может стартовать до завершения слоя N — смысл графа зависимостей теряется.

### C-5. «Retry с эскалацией» — заглушка
- [`retry_system.py:101-117`](../agents/retry_system.py:101): `_increase_priority`, `_critic_review`, `_meta_optimizer` содержат только `print` и `pass`.
- `update_task_status` в RetrySystem работает с `shared_context["tasks"]`, а он всегда `[]` ([`pipeline_executor.py:244`](../agents/pipeline_executor.py:244)) → вызов no-op; `retry_count` не растёт; `should_retry` нигде не используется.
- В итоге при провале весь конвейер (SDD→TDD→Coding→3×Critic→Meta) повторяется до 4 раз без изменения стратегии — дорого и бессмысленно. `AGENTS.md` («Улучшение №4 ✅») вводит в заблуждение.
- Тип `task_id`: `str` в RetrySystem, `int` в остальном коде.

### C-6. LOG16-интеграция мертва
- [`log16_integration.py:30`](../modules/log16_integration.py:30) импортирует `tool_registry`, а в [`core/core_tools.py`](../core/core_tools.py) есть только `_GLOBAL_REGISTRY`; `execute_registered_tool` не существует нигде в репозитории (проверено grep).
- `ImportError` проглатывается `except Exception` → `_enabled = False` всегда; пользователь видит «LOG16: загрузка контекста…», а запись в память не происходит. Покрытие 10% этого не ловит.

### C-7. Мета-оптимизатор перезаписывает промпт без валидации
- [`pipeline_executor.py:218-228`](../agents/pipeline_executor.py:218): вывод `deepseek-r1:32b` (с возможным `<think>…</think>` и markdown-обёрткой) пишется прямо в `coder_developer.txt`.
- Промпты используют `str.format` с плейсхолдерами; потерянный `{sdd_document}` или лишняя `{`/`}` ломает **все** следующие задачи с `KeyError`/`ValueError`.
- Нет бэкапа, отката, проверки плейсхолдеров, отметки в git. Срабатывает на любом провале одной задачи.

---

## 3. Серьёзные проблемы архитектуры

### A-1. Ядро загружается дважды, три источника правды
- `_core.py` исполняется через `exec_module` в [`core/__init__.py:15-18`](../core/__init__.py:15) и **ещё раз** в [`core/core.py:14-17`](../core/core.py:14) → два независимых модуля с разными `console`, состоянием и patch-точками.
- [`core/__init__.py:27-32`](../core/__init__.py:27) копирует атрибуты **снимком**: `core.call_ollama` ≠ то, что вызывает `BaseAgent.call_llm` (`core.core._root_core`). Мок/патч одного не влияет на другой — отсюда тесты вида `patch('core.core._root_core.call_ollama')` ([`tests/test_base_agent.py:23`](../tests/test_base_agent.py:23)).
- Hot reload `"_core"` ([`hot_reload.py:40`](../modules/hot_reload.py:40)) не работает: такого ключа нет в `sys.modules` (регистрируется `_root_core`).
- Дополнительно `sys.path.append` в [`_core.py:19`](../_core.py:19) и десятки `sys.path.insert` в тестах/tui — признак того, что проект не оформлен как пакет.
- **Рекомендация:** нормальный пакет (`pyproject.toml`, `pip install -e .`), `_core.py` → обычный модуль `core/runtime.py`, один `import`, явные зависимости вместо динамической «склейки».

### A-2. Зоны мутабельности (ADR-001) не исполняются кодом
- ADR вводит `kernel/supervised/autonomous`, но `hot_reload.ZONE_MODULES` — единственное место, где зоны вообще отражены; запрет записи в supervised-файлы агентом не проверяется ни в `dev_tools.write_file`, ни в `gate`.
- Заголовок [`_core.py:2-3`](../_core.py:2) всё ещё гласит «НЕИЗМЕНЯЕМОЕ ЯДРО … ИИ не имеет права менять» — противоречит ADR (supervised). То же в [`core/core.py:13`](../core/core.py:13).
- `ZONE_MODULES["autonomous"]` перечисляет не все модули и включает `modules.hot_reload` (перезагрузка самого себя).

### A-3. Facade `MigrationAgent` не доведён
- Остались мёртвый и опасный код: метод `_meta_recovery` **перекрыт** атрибутом `self._meta_recovery = None` ([`migration_agent.py:69`](../agents/migration_agent.py:69) vs [`:463`](../agents/migration_agent.py:463)) — вызов даст `TypeError`; `_execute_single_task` DEPRECATED, но ещё тут ([`:435`](../agents/migration_agent.py:435)); `_generate_plan_react` (≈100 строк) остаётся внутри фасада.
- Хак `'error' in dir()` ([`:408`](../agents/migration_agent.py:408)) вместо инициализации переменной.
- Ошибка в ветке `generate_plan`: при падении `build_repo_map` `project_scan` определяется, но в ветке `self._repo_map is None → else` нет (см. [`:175-185`](../agents/migration_agent.py:175)) — `UnboundLocalError` возможен при падении `DependencyPlanner`, если `_repo_map` уже задан.
- `MigrationAgent.run()` делает `sys.exit(1)` внутри метода агента — плохо для тестирования и переиспользования.

### A-4. Дублирование кода в ядре
- `load_prompt` ≡ `load_prompt_from_file`, `update_prompt_file` ≈ `update_prompt_in_file` ([`_core.py:25-80`](../_core.py:25)). (Тот же вывод был в [`architecture-review-20260924.md`](architecture-review-20260924.md), кандидат #4, — не устранён.)
- Два `TaskManager`-подобных: `agents/task_manager.py` и методы `RetrySystem.get/update_task_status` — разные файлы состояния, разные типы id.
- `agents/pipeline_executor.py` и `agents/migration_agent.py` оба несут логику `StepTrace`/`log16`.

### A-5. Конфигурация размазана и захардкожена
- `http://192.168.5.7:11434` в [`_core.py:15`](../_core.py:15), [`modules/llm/adapter.py:24`](../modules/llm/adapter.py:24), [`modules/eval/utils.py:9`](../modules/eval/utils.py:9). `OLLAMA_URL` в `_core.py` скорее всего не используется (всё идёт через adapter) — мёртвая константа.
- Имена моделей захардкожены в 4 местах (`agent.py`, `migration_agent.py`, `pipeline_executor.py`, `_core.py`); `deepseek-r1:32b` — строкой прямо в [`pipeline_executor.py:219`](../agents/pipeline_executor.py:219), при наличии [`model_profiles.json`](../model_profiles.json).
- `.env.example` и `python-dotenv` есть, но URL из env не читается (по grep).
- Относительные пути (`prompts.json`, `tasks.json`, `checkpoints`) зависят от CWD.

---

## 4. Качество кода

| ID | Проблема | Где |
|---|---|---|
| Q-1 | Проглатывание исключений (`except Exception: pass`), ≥15 мест, нет `logging` | `migration_agent.py:114,141,217`, `pipeline_executor.py:76,275`, `sandbox.py:147`, `log16_integration.py` (5 мест), `dev_tools.py:158` и др. |
| Q-2 | Мёртвая ветка: `if not is_valid and kwargs: pass` — валидация аргументов фактически игнорируется, вызов идёт с частичными kwargs | [`core/core.py:154-156`](../core/core.py:154) |
| Q-3 | Repair-цикл ReAct запрашивает «исправь вызов» **без истории диалога** — модель не видит свой прошлый ответ; кроме того, большая часть ошибок инструмента возвращается со статусом «успех» (`<tool_result>` с текстом «Ошибка…») и в repair вообще не попадает | [`core/core.py:87-123`](../core/core.py:87) |
| Q-4 | ReAct не накапливает историю: на каждом шаге в LLM уходит только последний `current_user` (без исходной задачи) — для многошаговых задач контекст теряется | [`core/core.py:81-84`](../core/core.py:81) |
| Q-5 | Парсер вызова находит только первый `<call>` (`re.search`), мульти-вызовы теряются | [`tool_parser.py:18-32`](../modules/tool_parser.py:18) |
| Q-6 | `run_isolated_tests` без `timeout` — зависший сгенерированный тест подвесит весь конвейер; выполняется в рабочем каталоге проекта, а не в изолированном | [`_core.py:97-104`](../_core.py:97) |
| Q-7 | `target_file` из LLM-сгенерированного `tasks.json` пишется без нормализации и проверки на выход за корень (`../`); `os.makedirs(os.path.dirname(target_file))` падает для файла без каталога (`''`) | [`pipeline_executor.py:158-160`](../agents/pipeline_executor.py:158) |
| Q-8 | Весь `shared_context` (со всеми SDD/кодами/тестами всех задач) сериализуется в промпты Critic и Meta → неограниченный рост контекста | [`pipeline_executor.py:193,215`](../agents/pipeline_executor.py:193) |
| Q-9 | Ключи в JSON после сохранения становятся строками, а код ищет по `int task_id` (`.get(task_id, {})`) — работает только за счёт fallback, при resume тихо ломается | [`pipeline_executor.py:126,145-146`](../agents/pipeline_executor.py:126) |
| Q-10 | Запись `tasks.json`/`shared_context.json`/`prompts.json` неатомарна (прямой `open(..., "w")`); сбой посреди записи → потеря состояния, а `load_tasks` при `JSONDecodeError` молча возвращает `{"tasks": []}` — миграция «успешно» завершится с нулём задач | [`task_manager.py:12-24`](../agents/task_manager.py:12) |
| Q-11 | Задачи, оставшиеся `in_progress` после падения процесса, никогда не подхватываются (берутся только `pending`) | [`migration_agent.py:355`](../agents/migration_agent.py:355) |
| Q-12 | Нет типизации контрактов: `execute()` в докстринге возвращает «(success, error)», по факту — `(task_id, success, error)`; `task: dict` без схемы | `pipeline_executor.py:26-65` |
| Q-13 | Эмодзи и промпт-фразы вшиты в код (`"Результат выполнения инструмента…"`, `"Сгенерируй тесты."`, `"Исправь ошибку."`), хотя AGENTS.md запрещает естественный язык в Python | `core.py`, `pipeline_executor.py`, `migration_agent.py` |

---

## 5. Безопасность исполнения

- [`dev_tools.run_command`](../modules/dev_tools.py:170) — `shell=True`; защита — только `confirm_action`. Приемлемо при реальном подтверждении человеком; но в режиме миграции (без TTY) поведение `confirm_action` по умолчанию нужно проверить (см. [`permissions.py`](../modules/permissions.py)) — **не проверено в этом обзоре**.
- `read_file`/`write_file`/`apply_diff` не ограничены корнем проекта; `read_file` свободен — модель может читать `.env`, ключи, `~/.ssh`.
- Код, сгенерированный LLM, исполняется в процессе-потомке без лимитов ресурсов, времени, сети (Q-6).
- Мета-самомодификация промптов (C-7) — вектор prompt-injection через содержимое легаси-кода → `test_log` → Meta-Optimizer → постоянный промпт.
- MCP-серверы по умолчанию слушают `127.0.0.1` — ок.

---

## 6. Зависимости, структура репозитория, тесты

- [`requirements.txt`](../requirements.txt): отсутствуют реально используемые `mcp`, `fastmcp`, `tree-sitter` (+ языковые грамматики) → чистая установка не запустит `agent.py` (`from mcp import Client` при импорте [`mcp_client.py:20`](../modules/mcp_client.py:20), вызывается на старте [`agent.py:28-29`](../agent.py:28)). `coverage` — dev-зависимость в runtime-списке. Нет `pyproject.toml`, нет lock-файла. AGENTS.md «только `requests` и `rich`» устарел.
- Корень захламлён: `eval_results*.json` (5 шт.), `prompts1.json`, `prompts/role_global_architect1.txt`, `role_tester_legacy.txt`, `project_code.py`, `gen_scaffold_test.py`, `test_core.py` рядом с `tests/`, `.coverage`.
- `modules/tui/` содержит 8 .md-файлов (CHANGES, FINAL_SUMMARY, IMPLEMENTATION_SUMMARY и т.д.) и `demo.py/example.py/examples_api.py` с собственной копией «загрузки ядра» — код-дубль и шум.
- `agent.py` на уровне импорта подключает MCP (сетевая побочка при `import`), любая подкоманда (`agent trace`) платит за это.
- **Покрытие:** агенты 0%, `eval/` 0%, `tui/` 0%, `log16_integration` 10%, `llm/adapter` 33%, `mcp_client` 32%, анализаторы Go/JS/PHP/TS 11–22%. Ядро и `modules` хорошо покрыты — но именно непокрытые части содержат дефекты C-1…C-7.
- Тестовый фреймворк по ADR — `unittest`; допустима смешанная структура (`test_core.py` в корне).

---

## 7. Расхождения документации и кода

| # | Документ | Утверждение | Факт |
|---|---|---|---|
| D-1 | AGENTS.md, Улучшение №2 | Промпты и LLM асинхронизируются через `asyncio.to_thread()` | Нет, вызовы синхронные (C-1) |
| D-2 | AGENTS.md, Улучшение №4 ✅ | Escalation Level 1–3 реализованы | Заглушки `pass` (C-5) |
| D-3 | AGENTS.md | `_core.py:147` использует `os.execv()` для hot reload; `OLLAMA_URL = …/api/generate` | `execv` заменён на `modules.hot_reload`; URL — `/api/chat`, файл 122 строки |
| D-4 | AGENTS.md / `_core.py` header | `_core.py` IMMUTABLE | ADR-001: supervised |
| D-5 | AGENTS.md | «Только `requests` и `rich`» | Нужны ещё `mcp`, `fastmcp`, `tree-sitter`, `python-dotenv` |
| D-6 | CONTEXT.md | Описывает `execute_all_parallel()`/`_execute_single_task_async()` | В коде их нет (`execute_all_with_retry` + `PipelineExecutor`) |
| D-7 | Rules (architect) | «Тесты сохраняются как `test_<filename>`» | Верно, но в корне проекта → коллизии (C-2) |

---

## 8. Сильные стороны (сохранить)

- Чёткая идея слоёв и ADR с зонами мутабельности — хорошая основа для самоэволюции.
- Мультиформатный парсер вызовов + `ToolRegistry` с автогенерацией JSON Schema из type hints.
- `PipelineExecutor`/`TaskManager`/`MetaRecovery` — правильное направление декомпозиции.
- Тесты ядра и `modules` на уровне 70–100%, `unittest`-инфраструктура, `coverage`.
- `modules/llm/adapter.py` с профилями моделей в [`model_profiles.json`](../model_profiles.json).
- MCP-серверы разложены по единому шаблону (server/tools/helpers).
- Журналы планов и ADR в `plans/`, `docs/adr/` — хорошая культура решений.

---

## 9. Приоритизированный план исправлений

### P0 — корректность (сначала тесты на агентов, потом фикс)
1. Тесты-характеризации для `PipelineExecutor` (StubLLM по [`test-crewai`-подходу](../tests/) не нужен — достаточно `unittest.mock` на `call_llm`), `TaskManager`, `RetrySystem`, `MigrationAgent.execute_all_with_retry`.
2. C-1 + C-2: `asyncio.to_thread` + `Semaphore`; общий `SharedContext` с `asyncio.Lock` и атомарной записью; уникальный каталог/имя тестового файла на задачу.
3. C-4: выполнение по слоям (`for layer in dependency_layers`).
4. C-3: либо `with Sandbox(...)` + `accept()` при успехе, либо удалить sandbox из конвейера (не использовать при параллельном выполнении; git-worktree на задачу как альтернатива).
5. C-7: валидация нового промпта (набор плейсхолдеров совпадает с прежним, удаление `<think>`), бэкап/коммит перед записью, откат при падении следующей задачи; не запускать мета-оптимизатор на каждом провале.
6. Q-6, Q-7, Q-10: таймаут тестов, нормализация `target_file` в корне проекта, атомарная запись состояния (`tempfile + os.replace`), ошибка вместо «пустого плана» при битом JSON.

### P1 — архитектура
7. A-1: единая загрузка ядра, оформление пакета (`pyproject.toml`), убрать `sys.path`-хаки и копию в `tui/*`.
8. C-5: реализовать или честно убрать эскалацию; единый `TaskStore` (см. кандидат #1 прошлого обзора), единый тип `task_id`.
9. C-6: починить LOG16 — публичный API реестра (`ToolRegistry.call(name, **kwargs)`), логировать причину отключения.
10. A-2: проверка зон мутабельности в `write_file/apply_diff` и в Meta-оптимизаторе (читать из `ZONE_MODULES`/ADR).
11. A-5: единый `Settings` (env + `model_profiles.json`): URL Ollama, имена моделей, пути.

### P2 — гигиена
12. Удалить мёртвый код (`_execute_single_task`, `_meta_recovery`-коллизия, `OLLAMA_URL`, дубли `load_prompt*`/`update_prompt*`).
13. Заменить `except Exception: pass` на `logging` + узкие исключения.
14. Q-3/Q-4: ReAct с историей сообщений (messages), нормальные ошибки инструментов.
15. Привести `requirements.txt`/`pyproject.toml` в соответствие; вынести `coverage` в dev.
16. Почистить корень и `modules/tui/*.md`; синхронизировать AGENTS.md / CONTEXT.md с кодом (D-1…D-7).
17. Подтянуть покрытие: `log16_integration`, `llm/adapter`, `mcp_client`, анализаторы Go/JS/PHP/TS.

---

## 10. Что стоит перепроверить отдельно (не охвачено)

- `modules/permissions.py::confirm_action` в неинтерактивном режиме (миграция в фоне).
- `modules/tool_parser.py` целиком, `modules/gate.py`, `modules/eval/*`, `modules/tui/*`.
- Реальное поведение Sandbox на грязном дереве при запуске миграции (ожидаем `SandboxError`, глотается).
- Совместимость `importlib.reload` с экземплярами классов агентов, живущих в процессе (после reload старые объекты остаются на старых классах).
