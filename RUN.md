# 🚀 Запуск проекта с использованием venv

Краткое руководство по установке и запуску **Autonomous AI Software Engineer v1.0** через виртуальное окружение `venv`.

---

## 📋 Требования

| Требование | Значение |
|------------|----------|
| Python | 3.10+ (рекомендуется 3.11, как в `Dockerfile`) |
| Ollama | запущенный локально, ответы на `OLLAMA_BASE_URL` |
| OS | Linux / macOS / Windows |
Зависимости проекта объявлены в [`pyproject.toml`](pyproject.toml):

- `requests` — вызовы Ollama API
- `rich>=13.0.0` — терминальный вывод и TUI
- `python-dotenv` — загрузка переменных из `.env`
- `mcp`, `fastmcp` — MCP-клиент и MCP-серверы
- `tree-sitter` (+ грамматики `python`/`php`/`javascript`/`typescript`/`go`) — анализ кода


---

## 1️⃣ Создание виртуального окружения

Из корня проекта:

```bash
# Linux / macOS
python3 -m venv venv
source venv/bin/activate

# Windows (Git Bash / PowerShell)
py -m venv venv
venv\Scripts\activate
```

После активации в приглашении терминала появится префикс `(venv)`.

> ⚠️ Папка `venv/` является **IMMUTABLE** — не редактируйте и не удаляйте её содержимое вручную.

---

## 2️⃣ Установка проекта и зависимостей

Проект оформлен как пакет ([`pyproject.toml`](pyproject.toml)). Устанавливаем его в
редактируемом режиме вместе с зависимостями:

```bash
pip install --upgrade pip
pip install -e .
```

Для разработки (тесты с покрытием):

```bash
pip install -e ".[dev]"
```

Проверка установки:

```bash
pip list
```

---

## 3️⃣ Настройка окружения (.env)

Файл-образец: [`.env.example`](.env.example)

1. Скопируйте образец в рабочий файл:

   ```bash
   cp .env.example .env
   ```

2. Отредактируйте `.env` под своё окружение:

   ```ini
   OLLAMA_BASE_URL=http://192.168.5.7:11434
   ARCHITECT_MODEL=qwen3-coder:30b
   CODER_MODEL=qwen2.5-coder:14b
   META_MODEL=deepseek-r1:32b
   TEST_TIMEOUT=300
   MAX_CONCURRENCY=2
   TRACES_DIR=traces
   MAX_SESSIONS=20
   MCP_SERVER_URL=http://localhost:3000
   ```

> ℹ️ `OLLAMA_BASE_URL` указывается **без** пути `/api/...` — конкретный endpoint
> (`/api/chat`) добавляет адаптер. Переменные читаются через
> [`modules/settings.py`](modules/settings.py) (единый источник правды: там же
> дефолты для URL и имён моделей).

---

## 4️⃣ Запуск основного агента (миграция легаси-кода)

Точка входа — [`agent.py`](agent.py) (эта же команда используется в [`Dockerfile`](Dockerfile:21)):

```bash
python agent.py
```

Агент прочитает манифест, создаст задачи и запустит конвейер:

```
manifest.json → Global Architect → SDD → TDD → Coding → Tests
```

Параллельное выполнение, retry и эскалация обрабатываются внутри `MigrationAgent` автоматически.

---

## 5️⃣ Запуск TUI (текстовый интерфейс)

### Демо-режим

```bash
python -m modules.tui.demo --mode full
```

Доступные режимы: `simple`, `events`, `live`, `chat`, `help`, `full`.

### Режимы через API-пример TUI

```bash
python -m modules.tui.examples_api --mode simple
python -m modules.tui.examples_api --mode demo
python -m modules.tui.examples_api --mode integration
```

`--mode integration` подключает TUI к реальному `MigrationAgent`.

### Простой пример

```bash
python -m modules.tui.example
```

---

## 6️⃣ Запуск тестов

Тесты написаны на `unittest` и запускаются строго через `subprocess.run()` — критерий успеха только `returncode == 0`.

Тесты разбиты по доменам в пакете [`tests/`](tests/). Корневой раннер [`test_core.py`](test_core.py) запускает их все через `unittest discover`.

```bash
# Все тесты
python test_core.py

# Или через unittest discover
python -m unittest discover tests -v

# Отдельные тестовые модули
python -m unittest tests.test_base_agent -v
python -m unittest tests.test_tracer -v
python -m unittest tests.test_gate -v
python -m unittest tests.test_scaffold -v
```

---

## 🧹 Деактивация и повторный запуск

```bash
# Выйти из окружения
deactivate

# Повторно активировать позже
source venv/bin/activate   # Linux / macOS
venv\Scripts\activate      # Windows
```

---

## 🐳 Альтернатива: запуск в Docker

Если не хотите настраивать venv, доступен готовый контейнер (см. [`Dockerfile`](Dockerfile)):

```bash
docker build -t ai-agent .
docker run -it ai-agent
```

---

## ⚠️ Критических правил

- Зона **supervised** ([`core/core.py`](core/core.py), [`core/runtime.py`](core/runtime.py),
  [`core/core_tools.py`](core/core_tools.py), [`core_tools.py`](core_tools.py)) — изменения
  требуют подтверждения человека (y/n). См. [`ADR-001`](docs/adr/ADR-001-core-boundaries.md).
- Папка `venv/` — **IMMUTABLE**.
- Промпты живут в [`prompts/`](prompts/) (и в [`prompts.json`](prompts.json)) как внешние файлы — никаких промптов внутри кода.
