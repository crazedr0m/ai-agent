# План реструктуризации test_core.py

## Цель

Разбить монолитный [`test_core.py`](../test_core.py) (692 строки, 13 тестовых классов)
на пакет `tests/` с отдельными файлами по доменам. Gate и Scaffold продолжают работать.

---

## Итоговая структура

```
test_core.py              ← корневой раннер (discover tests/)
tests/
  __init__.py
  test_base_agent.py      ← TestBaseAgent + TestExecuteToolCall
  test_tool_registry.py   ← TestToolRegistry + TestToolsIntegration
  test_tracer.py          ← TestTracer
  test_mcp_manager.py     ← TestMCPManager
  test_mcp_filesystem.py  ← TestMCPServerFilesystem
  test_mcp_fetch.py       ← TestMCPServerFetch
  test_sandbox.py         ← TestPhase4Sandbox
  test_gate.py            ← TestPhase4Gate
  test_retrospective.py   ← TestPhase4Retrospective
  test_scaffold.py        ← TestPhase4Scaffold
  test_hot_reload.py      ← TestPhase4HotReload
```

---

## Поэтапный план

### Этап 1: Создать пакет `tests/` с файлами-модулями

Для каждого из 13 тестовых классов — свой файл в `tests/`.

**Ключевые решения:**

1. **`sys.path.insert(0, ...)`** — вынести в `tests/__init__.py`:
   ```python
   import sys, os
   sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
   ```
   Каждый тестовый файл делает `from tests import *` или `from tests import common_setup`.

   **Альтернатива:** оставить `sys.path` в каждом файле отдельно.
   **Рекомендация:** через `__init__.py`, чтобы не дублировать в 13 файлах.

2. **Общие хелперы** (например, `create_temp_dir` и т.д.) — в `tests/__init__.py` или отдельный `tests/helpers.py`. Сейчас дублирования почти нет — каждый класс сам создаёт `tmpdir`, `setUp`. Оставляем как есть, каждый файл самодостаточен.

3. **Импорты** — каждый файл импортирует только то, что нужно. Сейчас `test_core.py` импортирует всё сразу.

**Состав файлов:**

#### `tests/__init__.py`
```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

#### `tests/test_base_agent.py` — строки 22–131 + 486–514 из test_core.py
Классы: `TestBaseAgent`, `TestExecuteToolCall`
Импорты: `unittest`, `unittest.mock`, `os`, `json`, `tempfile`, `shutil`, `core`, `core.core`

Особенности:
- `TestBaseAgent.setUp()` мокает `core.core._root_core.call_ollama`
- `TestExecuteToolCall.setUp()` импортирует `core_tools` для регистрации инструментов
- `test_agent_load_prompt()` создаёт временную директорию с `prompts.json`

#### `tests/test_tool_registry.py` — строки 133–193 + 454–483 из test_core.py
Классы: `TestToolRegistry`, `TestToolsIntegration`
Импорты: `unittest`, `os`, `core.core_tools`, `core_tools`

Особенности:
- `TestToolsIntegration.test_tools_registered_via_decorator()` импортирует `core_tools` для регистрации

#### `tests/test_tracer.py` — строки 196–284 из test_core.py
Класс: `TestTracer`
Импорты: `unittest`, `os`, `json`, `tempfile`, `shutil`, `modules.tracer`

Особенности:
- `setUp`/`tearDown` — временная директория для трейсов

#### `tests/test_mcp_manager.py` — строки 287–349 из test_core.py
Класс: `TestMCPManager`
Импорты: `unittest`, `modules.mcp_client`

Особенности:
- Тестирует конфигурацию без реального подключения

#### `tests/test_mcp_filesystem.py` — строки 352–431 из test_core.py
Класс: `TestMCPServerFilesystem`
Импорты: `unittest`, `os`, `tempfile`, `shutil`, `mcp_servers.filesystem.tools`

Особенности:
- `setUp` — создаёт `tmpdir`, пишет `test.txt`, создаёт `subdir/nested.py`
- Контрактные тесты для каждого инструмента

#### `tests/test_mcp_fetch.py` — строки 434–451 из test_core.py
Класс: `TestMCPServerFetch`
Импорты: `unittest`, `mcp_servers.fetch.tools`

Особенности:
- Тестирует только невалидные URL (нет сети)

#### `tests/test_sandbox.py` — строки 517–541 из test_core.py
Класс: `TestPhase4Sandbox`
Импорты: `unittest`, `os`, `tempfile`, `shutil`, `modules.sandbox`

Особенности:
- Требует временной директории без git

#### `tests/test_gate.py` — строки 544–579 из test_core.py
Класс: `TestPhase4Gate`
Импорты: `unittest`, `sys`, `modules.gate`

#### `tests/test_retrospective.py` — строки 582–616 из test_core.py
Класс: `TestPhase4Retrospective`
Импорты: `unittest`, `os`, `json`, `tempfile`, `modules.retrospective`

#### `tests/test_scaffold.py` — строки 619–651 из test_core.py
Класс: `TestPhase4Scaffold`
Импорты: `unittest`, `modules.scaffold`

#### `tests/test_hot_reload.py` — строки 654–689 из test_core.py
Класс: `TestPhase4HotReload`
Импорты: `unittest`, `modules.hot_reload`, `core`

---

### Этап 2: Написать корневой `test_core.py` как тонкий раннер

Новый [`test_core.py`](../test_core.py) заменяет 692 строки на ~20:

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# test_core.py — Корневой раннер тестов
#
# Запускает все тесты из пакета tests/ через unittest discover.
#
# Использование:
#   python test_core.py              # все тесты
#   python -m unittest discover      # то же самое

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == '__main__':
    test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tests')
    suite = unittest.TestLoader().discover(test_dir, pattern='test_*.py')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
```

**Проверка:** `python test_core.py` должен возвращать `returncode == 0` и выводить все тесты.

---

### Этап 3: Обновить [`modules/gate.py`](../modules/gate.py)

**Изменения минимальны** — `test_core.py` как раннер сохраняется.

1. Строка 46: команда не меняется — `[sys.executable, "test_core.py"]` продолжает работать.

2. Строки 31–33: обновить docstring:
   ```
   # Проверяет три уровня:
   # 1. Тесты — `python test_core.py` (discover tests/) должен вернуть 0
   ```

**Итог:** Gate не требует изменений логики, только косметика документации.

---

### Этап 4: Переписать [`modules/scaffold.py`](../modules/scaffold.py) — генерация тестов в `tests/`

Текущий механизм (`_create_tool_test`, `_create_module_test`, `_create_mcp_test`) дописывает код в `test_core.py` методом `_append_to_test_file`, который парсит Python-файл — это хрупко.

**Новый подход:** каждый тест — отдельный файл `tests/test_<name>.py`.

#### 4.1. `_create_tool_test(name, filename)` → `tests/test_<name>.py`

```python
def _create_tool_test(self, name: str, filename: str):
    """Создать файл tests/test_<name>.py для нового инструмента."""
    test_code = f'''# -*- coding: utf-8 -*-
# tests/test_{name}.py — Тест для инструмента {name}

import unittest
from core.core_tools import get_tool


class Test{name.capitalize()}(unittest.TestCase):
    """Тесты для инструмента {name}."""

    def test_{name}_executes(self):
        \"\"\"{name} возвращает результат.\"\"\"
        tool = get_tool("{name}")
        self.assertIsNotNone(tool)
        result = tool("test")
        self.assertIn("executed", result)


if __name__ == "__main__":
    unittest.main()
'''
    test_path = os.path.join(self.repo_path, 'tests', f'test_{name}.py')
    os.makedirs(os.path.dirname(test_path), exist_ok=True)
    with open(test_path, "w", encoding="utf-8") as f:
        f.write(test_code)
```

#### 4.2. `_create_module_test(name, filename)` → `tests/test_<name>.py`

```python
def _create_module_test(self, name: str, filename: str):
    """Создать файл tests/test_<name>.py для нового модуля."""
    class_name = name.capitalize()
    test_code = f'''# -*- coding: utf-8 -*-
# tests/test_{name}.py — Тест для модуля {name}

import unittest
from modules.{name} import {class_name}


class Test{class_name}(unittest.TestCase):
    """Тесты для модуля {name}."""

    def test_{name}_runs(self):
        \"\"\"{name} запускается без ошибок.\"\"\"
        instance = {class_name}()
        result = instance.run()
        self.assertIn("executed", result)


if __name__ == "__main__":
    unittest.main()
'''
    test_path = os.path.join(self.repo_path, 'tests', f'test_{name}.py')
    os.makedirs(os.path.dirname(test_path), exist_ok=True)
    with open(test_path, "w", encoding="utf-8") as f:
        f.write(test_code)
```

#### 4.3. `_create_mcp_test(name, filename)` → `tests/test_mcp_<name>.py`

```python
def _create_mcp_test(self, name: str, filename: str):
    """Создать файл tests/test_mcp_<name>.py для нового MCP-сервера."""
    test_code = f'''# -*- coding: utf-8 -*-
# tests/test_mcp_{name}.py — Тест для MCP-сервера {name}

import unittest
from mcp_servers.{name}.tools import ping


class TestMCP{name.capitalize()}(unittest.TestCase):
    """Тесты для MCP-сервера {name}."""

    def test_mcp_{name}_ping(self):
        \"\"\"MCP-сервер {name} отвечает на ping.\"\"\"
        result = ping()
        self.assertEqual(result, "pong")


if __name__ == "__main__":
    unittest.main()
'''
    test_path = os.path.join(self.repo_path, 'tests', f'test_mcp_{name}.py')
    os.makedirs(os.path.dirname(test_path), exist_ok=True)
    with open(test_path, "w", encoding="utf-8") as f:
        f.write(test_code)
```

#### 4.4. Удалить `_append_to_test_file()` и `_find_method_end()`

Оба метода больше не нужны. Scaffold становится чище и проще.

---

### Этап 5: Обновить документацию

#### [`RUN.md`](../RUN.md): раздел «Тестирование» (строки 133–146)

Было:
```markdown
# Все тесты
python -m unittest discover -v

# Отдельные файлы
python -m unittest test_core -v
python -m unittest test_app -v

# Либо напрямую
python test_core.py
python test_app.py
```

Стало:
```markdown
# Все тесты
python test_core.py

# Отдельные тестовые модули
python -m unittest tests.test_base_agent -v
python -m unittest tests.test_tracer -v

# Через unittest discover
python -m unittest discover tests -v
```

#### [`docs/adr/ADR-001-core-boundaries.md`](../docs/adr/ADR-001-core-boundaries.md)

Проверить, нет ли упоминаний `test_core.py`. Если есть — обновить.
В текущей версии `test_core.py` не упоминается — ADR не требует изменений.

#### Другие файлы, которые могут ссылаться на `test_core.py`:

- `modules/eval_harness.py` — упоминает `test_core.py` только в тестовых данных eval (строка 69), не требует изменений.
- `modules/gate.py` — см. Этап 3.
- `modules/scaffold.py` — см. Этап 4.

---

### Этап 6: Верификация

1. **`python test_core.py`** — `returncode == 0`, все тесты проходят, вывод:
   ```
   test_mcp_filesystem.py ... OK
   test_base_agent.py ... OK
   ...
   ----------------------------------------------------------------------
   Ran 54 tests in X.XXs
   OK
   ```

2. **`python -m unittest discover tests`** — то же самое.

3. **`python -m unittest tests.test_base_agent -v`** — один файл запускается.

4. **Тест Gate:** импорт `Gate` и вызов `gate.check()` (с заглушкой subprocess) — работает.

5. **Тест Scaffold:** вызов `sc.create_tool("test_tool")` создаёт файл в `tests/`.

6. **Проверка `sys.path`:** `tests/__init__.py` корректно настраивает путь — `import core`, `from core.core import *` работают из любого тестового файла.

---

## Контрольные точки (checkpoints)

| # | Что проверяем | Критерий |
|---|--------------|----------|
| CP1 | Создан пакет `tests/` | `ls tests/` показывает 13 файлов + `__init__.py` |
| CP2 | Корневой `test_core.py` | `python test_core.py` → `OK (54 tests)` |
| CP3 | Gate не сломан | `python -c "from modules.gate import Gate; g=Gate(); g._check_tests()"` |
| CP4 | Scaffold генерирует в `tests/` | `sc.create_tool("foo")` → `tests/test_foo.py` существует |
| CP5 | `RUN.md` обновлён | `grep "tests/" RUN.md` показывает новые команды |
| CP6 | `test_app.py` (если существует) | Проверить, не ссылается ли он на старую структуру |

---

## Риски

| Риск | Вероятность | Митигация |
|------|------------|-----------|
| `sys.path` не настроен при запуске отдельных файлов | Средняя | `__init__.py` с `sys.path.insert(0, ...)` + каждый файл импортирует `from tests import *` |
| Кто-то запускает `python tests/test_base_agent.py` напрямую | Низкая | Добавить `if __name__ == '__main__'` в каждый файл |
| Gate продолжает ссылаться на старый `test_core.py` | Низкая | Gate не меняет команду — раннер сохраняется |
| Scaffold сломан при генерации тестов для existing модулей | Средняя | Тестировать через `sc.create_tool("foo", description="Test")` после миграции |

---

## Диаграмма потока запуска тестов

```mermaid
flowchart TD
    A["python test_core.py"] --> B["test_core.py runner<br/>discover('tests/', 'test_*.py')"]
    B --> C1["tests/test_base_agent.py"]
    B --> C2["tests/test_tool_registry.py"]
    B --> C3["tests/test_tracer.py"]
    B --> C4["tests/test_mcp_manager.py"]
    B --> C5["tests/test_mcp_filesystem.py"]
    B --> C6["tests/test_mcp_fetch.py"]
    B --> C7["tests/test_sandbox.py"]
    B --> C8["tests/test_gate.py"]
    B --> C9["tests/test_retrospective.py"]
    B --> C10["tests/test_scaffold.py"]
    B --> C11["tests/test_hot_reload.py"]
    B --> C12["tests/test_base_agent.py<br/>(TestExecuteToolCall)"]
    B --> C13["tests/test_tool_registry.py<br/>(TestToolsIntegration)"]
    
    D["python -m unittest discover tests -v"] -.-> B
    E["python -m unittest tests.test_gate -v"] -.-> C8