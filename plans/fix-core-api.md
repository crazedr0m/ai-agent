# План: Добавление недостающего API в core.py

## Проблема

В [`modules/executor.py`](modules/executor.py) и [`initializer.py`](initializer.py) вызываются три функции, которых нет в [`core.py`](core.py):

| Вызов | Где | Статус |
|---|---|---|
| `core.load_prompt_from_file("sdd_architect")` | executor.py:20,36,50,82,102; initializer.py:57 | ❌ Отсутствует |
| `core.update_prompt_in_file("coder_developer", ...)` | executor.py:114; docs/example.md:27 | ❌ Отсутствует |
| `core.call_ollama(..., model_override="...")` | executor.py:27,111; initializer.py:69 | ❌ Не принимает параметр |

## Изменения

### 1. [`core.py`](core.py) — добавить `load_prompt_from_file(role_key)`

```python
def load_prompt_from_file(role_key: str) -> str:
    """Загружает промпт: из файла (file_path) или inline (prompt)."""
    with open("prompts.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    entry = data[role_key]
    if "file_path" in entry:
        with open(entry["file_path"], "r", encoding="utf-8") as pf:
            return pf.read()
    return entry["prompt"]
```

**Логика**: [`prompts.json`](prompts.json) содержит два типа записей:
- `sdd_architect`, `tdd_tester`, `coder_developer`, `critic_debugger` — с ключом `file_path` (чтение из `prompts/*.txt`)
- `role_tester`, `role_critic_optimizer`, `role_global_architect` — с ключом `prompt` (inline текст)

Функция читает из файла если есть `file_path`, иначе возвращает inline `prompt`.

### 2. [`core.py`](core.py) — добавить `update_prompt_in_file(role_key, new_text)`

```python
def update_prompt_in_file(role_key: str, new_text: str) -> bool:
    """Обновляет файл промпта с проверкой mutability."""
    with open("prompts.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    entry = data[role_key]
    if entry.get("mutability") == "immutable":
        console.print(f"[red]🚫 Блокировка: {role_key} immutable[/red]")
        return False
    file_path = entry.get("file_path", f"prompts/{role_key}.txt")
    with open(file_path, "w", encoding="utf-8") as pf:
        pf.write(new_text)
    console.print(f"[green]✅ Промпт {role_key} обновлён в {file_path}[/green]")
    return True
```

**Логика**: Аналог [`core.update_prompt_file()`](core.py:66), но для `file_path`-записей (обновляет файл на диске, а не inline поле в JSON).

### 3. [`core.py`](core.py) — модифицировать `call_ollama()`

```python
def call_ollama(system_prompt: str, user_prompt: str, model_override: str = None) -> str:
    model = model_override or ANALYZER_MODEL
    # ... остальной код без изменений, payload["model"] = model
```

**Логика**: Параметр `model_override` опциональный. Если не передан — используется `ANALYZER_MODEL` ("qwen2.5-coder:14b"), как и раньше. Обратная совместимость полная.

## Проверка совместимости

Все три изменения **не ломают** существующий код:
- `load_prompt()` — не меняется, продолжает читать inline `prompt`
- `update_prompt_file()` — не меняется, продолжает обновлять inline поле
- `call_ollama(system, user)` — работает без `model_override` как и раньше