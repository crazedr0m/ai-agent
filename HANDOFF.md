# 📋 Handoff Document: Развитие AI-агента ai-agent (Часть 8)

---

## 🎯 Текущее состояние задачи

**Задача:** Глубокий анализ архитектуры саморазвивающегося AI-агента для выявления точек роста и улучшения. Анализ завершён, требуется принятие решений по развитию системы.

**Статус:** Проведён детальный анализ проекта. Ожидается утверждение приоритетов улучшений пользователем.

---

## 📂 Обзор проекта

### Архитектура

```
ai-agent/
├── core/              # Ядро (IMMUTABLE)
│   ├── core.py       # BaseAgent + ReActEngine
│   └── core_tools.py # Инструменты (list_dir, read_file, и т.д.)
├── agents/           # Агенты
│   └── migration_agent.py  # Главный агент миграции
├── modules/          # Модули
│   ├── tracer.py     # Трейсер ReAct-цикла (JSONL)
│   └── parser.py     # Парсинг кода из markdown
├── prompts/          # Промпты агентов (.txt файлы)
├── legacy_src/       # Исходный код (Flask + SQLAlchemy синхронный)
├── modern_src/       # Целевой код (FastAPI + SQLAlchemy Async)
└── migration_manifest.json  # Конфиг миграции
```

### Доменная модель

| Термин | Описание |
|--------|----------|
| **Agent** | Режим работы системы, наследующий `BaseAgent` |
| **BaseAgent** | Абстрактный класс с ReAct-циклом |
| **ReActEngine** | Цикл: LLM → парсинг вызова → выполнение инструмента → запись трейса |
| **ToolRegistry** | Реестр инструментов через декоратор `@register_tool` |
| **TraceSession** | Менеджер сессии трейсинга (JSONL, ротация) |

---

## 🔄 Конвейер выполнения

```
manifest.json → Global Architect (создаёт tasks.json)
  → SDD (архитектурный план, 30B модель)
    → TDD (генерация тестов ДО кода)
      → Coding (написание реализации)
        → Тесты (returncode проверка)
          → Успех → следующая задача
          → Провал → Critic (до 3 попыток)
            → Тупик → Meta-Optimizer → перезапись prompts/ → Hot Reload
```

---

## 📊 Текущее состояние миграции

### Legacy Project (`legacy_src/`)

**Технологии:**
- Flask (синхронный)
- SQLAlchemy 1.x (синхронный ORM)
- SQLite база данных

**API эндпоинты:**
- `GET /api/products` — список товаров
- `POST /api/products` — создание товара
- `POST /api/orders` — создание заказа
- `GET /api/users/<id>` — получение пользователя
- `POST /api/users` — создание пользователя

**Модели данных:**
- `User` (id, name, email)
- `Product` (id, name, price, stock)
- `Order` (id, user_id, total, created_at)
- `OrderItem` (id, order_id, product_id, quantity, price)

### Target Project (`modern_src/`)

**Целевые технологии:**
- FastAPI (асинхронный)
- SQLAlchemy v2.0 Async ORM
- Pydantic v2 валидация
- SQLite база данных

**Конstraints:**
- ✅ Строго сохранять обратную совместимость REST API
- ✅ НЕ изменять схему таблиц БД
- ✅ Весь новый код асинхронный (async/await)
- ✅ Покрытие тестами ≥ 80%

---

## 🔍 Ключевые наблюдения (резюме анализа)

### 1️⃣ **ReActEngine** — Точка контроля №1

**Файл:** [`core/core.py`](core/core.py:28)

```python
class ReActEngine:
    def __init__(self, ..., max_steps: int = 10, ...):
```

- ✅ Имеет `max_steps=10` по умолчанию
- ❌ **НО!** В [`migration_agent.py`](agents/migration_agent.py:18) — `MAX_REACT_STEPS = 7` — это ограничение!
- 🔴 **Проблема:** Hard-coded лимит в конвейере агента перекрывает гибкость ReActEngine

**Рекомендация:** Сделать `max_steps` настраиваемым через манифест, а не hard-coded.

---

### 2️⃣ **MigrationAgent.run()** — Точка входа

**Файл:** [`agents/migration_agent.py`](agents/migration_agent.py:49)

```python
def run(self):
    # 1. Загружаем манифест ✅
    # 2. Инициализируем трейсер ✅
    # 3. Генерируем план через generate_plan() ❗
    # 4. execute_all() — последовательная итерация
```

- 🔴 **Критично:** `execute_all()` выполняет задачи **последовательно**, не параллельно
- 🔴 **Критично:** При ошибке задача помечается как `failed` без возможности восстановления
- 🟡 **Вопрос:** Нужна ли система восстановления после ошибок (retry with escalation)?

---

### 3️⃣ **Конвейер SDD → TDD → Coding** — Точка контроля №2

**Файл:** [`agents/migration_agent.py`](agents/migration_agent.py:159)

```python
def _execute_single_task(self, task: dict) -> bool:
    # ── SDD ──
    sdd_doc = self.call_llm(sdd_system, sdd_user, model_override=self.model_architect)
    
    # ── TDD ──
    raw_test = self.call_llm(test_system, "Сгенерируй тесты.")
    
    # ── Coding ──
    code_doc = self.call_llm(coding_system, coding_user, model_override=self.model_coder)
```

- 🔴 **Критично:** Каждый шаг — отдельный `call_llm()` без сохранения контекста между шагами
- 🔴 **Критично:** SDD → TDD → Coding работают изолированно, теряется контекст
- 🟡 **Вопрос:** Нужен ли shared context между этапами конвейера?

---

### 4️⃣ **Critic + Meta-Optimizer** — Точка контроля №3

**Файл:** [`agents/migration_agent.py`](agents/migration_agent.py:265)

```python
def _meta_recovery(self, raw_response: str, error: Exception, step: int) -> bool:
    """Meta-Optimizer: перезапись промптов после тупика."""
```

- 🔴 **Критично:** Meta-Optimizer перезаписывает промпты **только после полного тупика** (3 попытки + 3 итерации)
- 🔴 **Критично:** Нет ранней адаптации промптов на основе ошибок
- 🟡 **Вопрос:** Нужна ли динамическая адаптация промптов в реальном времени?

---

## 📝 Предстоящие шаги

1. **Ждать утверждения приоритетов улучшений пользователем**
2. **Реализовать выбранные улучшения по приоритету**
3. **Обновить документацию при изменении поведения системы**
4. **Провести регрессионное тестирование после изменений**

---

## 💡 Рекомендации по дальнейшему развитию

1. **Meta-Agent v2** — агент саморазвития для анализа трейсов и улучшения промптов
2. **Human-in-the-loop** — возможность вмешательства человека в критические решения
3. **Metrics & Observability** — метрики выполнения, latency, success rate
4. **Modular agents** — возможность динамической подмены агентов конвейера

---

## 📂 Ключевые файлы для работы

| Файл | Путь | Значение |
|------|------|----------|
| AGENTS.md | [`/home/giv/www/ai-agent/AGENTS.md`](AGENTS.md) | Описание архитектуры агентов и правил |
| CONTEXT.md | [`/home/giv/www/ai-agent/CONTEXT.md`](CONTEXT.md) | Терминология и доменная модель |
| core/core.py | [`/home/giv/www/ai-agent/core/core.py`](core/core.py) | BaseAgent + ReActEngine |
| agents/migration_agent.py | [`/home/giv/www/ai-agent/agents/migration_agent.py`](agents/migration_agent.py) | Главный агент миграции |
| migration_manifest.json | [`/home/giv/www/ai-agent/migration_manifest.json`](migration_manifest.json) | Конфиг манифеста |
| prompts.json | [`/home/giv/www/ai-agent/prompts.json`](prompts.json) | Промпты агентов |
| modules/tracer.py | [`/home/giv/www/ai-agent/modules/tracer.py`](modules/tracer.py) | Трейсер ReAct-цикла |

---

*Handoff создан для обеспечения непрерывности работы над развитием AI-агента.*