# ADR-002: Мультиязычный статический анализатор — единый сервер с языковыми модулями

## Статус

Принят (27.10.2026)

## Контекст

Существующий MCP-сервер `code_analyzer` работает только с Python через `tree-sitter-python`. Требуется расширить анализ на PHP, JavaScript, TypeScript и Go. Ключевое требование — cross-language анализ связки PHP→HTML→JS (легаси-спагетти, где PHP `echo` генерирует JS-код с интерполяцией PHP-переменных, и нужно резолвить символы в `.js`-файлах).

### Рассмотренные варианты

**Вариант A: Единый сервер с языковыми модулями**
- Один FastMCP-процесс `code-analyzer`
- Все языковые парсеры (tree-sitter-python, tree-sitter-php, tree-sitter-javascript, tree-sitter-typescript, tree-sitter-go) загружены в один процесс
- Cross-language анализ: PHP→HTML→JS в общей памяти
- Одна запись в `mcp_servers.json`, один TCP-порт

**Вариант B: N отдельных серверов**
- `php-analyzer`, `js-analyzer`, `ts-analyzer`, `go-analyzer` — каждый свой процесс
- Каждый — свой FastMCP, свой порт, своя запись в конфиге
- Cross-language анализ требует межпроцессного взаимодействия (HTTP/сокет)

### Ключевые tradeoffs

| Критерий | Вариант A (единый) | Вариант B (N серверов) |
|----------|-------------------|----------------------|
| Cross-language анализ | Естественно в одном процессе | Требует IPC, latency, complexity |
| Изоляция сбоев | Один процесс — один point of failure | Краш одного не валит остальные |
| Потребление памяти | Все парсеры в одном процессе (heavy) | Распределено по процессам |
| DevOps | Один деплой, один healthcheck | N деплоев, N healthcheck'ов |
| Переиспользование кода | 70% shared (кэш, обход AST, инструменты) | Дублирование инфраструктуры |

## Решение

**Выбран Вариант A: единый сервер $code-analyzer с языковыми модулями.**

### Архитектура

```
mcp_servers/code_analyzer/
├── __init__.py              # main(), экспорт инструментов
├── server.py                # FastMCP("code-analyzer", ...)
├── tools.py                 # MCP-инструменты (scan_project, query_*)
│
├── core.py                  # Ядро: кэш AST, _parse_file, _get_text, _get_all_files
│
├── languages/
│   ├── __init__.py           # registry: get_parser("python") → PythonAnalyzer
│   ├── base.py               # AbstractAnalyzer (интерфейс для всех языков)
│   ├── python/               # Существующий Python-анализ
│   │   ├── __init__.py
│   │   └── analyzer.py       # PythonAnalyzer(BaseAnalyzer)
│   ├── php/                  # PHP + PHP→HTML→JS pipeline
│   │   ├── __init__.py
│   │   ├── analyzer.py       # PhpAnalyzer(BaseAnalyzer)
│   │   └── string_detector.py # Детекция HTML/JS/CSS в строковых литералах
│   ├── javascript/
│   │   ├── __init__.py
│   │   └── analyzer.py       # JavaScriptAnalyzer(BaseAnalyzer)
│   ├── typescript/
│   │   ├── __init__.py
│   │   └── analyzer.py       # TypeScriptAnalyzer(BaseAnalyzer)
│   └── go/
│       ├── __init__.py
│       └── analyzer.py       # GoAnalyzer(BaseAnalyzer)
│
├── cross_language/
│   ├── __init__.py
│   ├── php_js_bridge.py      # PHP→HTML→JS: chain парсинга
│   └── graph_merger.py       # Слияние графов вызовов между языками
│
└── tests/
    ├── test_core.py
    ├── test_php_analyzer.py
    ├── test_js_analyzer.py
    ├── test_ts_analyzer.py
    ├── test_go_analyzer.py
    └── test_php_js_bridge.py
```

### Интерфейс BaseAnalyzer

```python
class BaseAnalyzer(ABC):
    language: str                         # "python" | "php" | "javascript" | "typescript" | "go"
    language_id: Language                 # tree-sitter Language object
    parser: Parser                        # tree-sitter Parser
    
    @abstractmethod
    def collect_definitions(self, filepath: str) -> Definitions: ...
    
    @abstractmethod
    def get_symbol_signature(self, filepath: str, symbol_name: str) -> Signature | None: ...
    
    @abstractmethod
    def build_call_graph(self, filepath: str) -> dict[str, list[str]]: ...
```

### PHP→HTML→JS pipeline

```
PHP-файл
  → Tree-sitter PHP парсер (php/analyzer.py)
    → string_detector.py: найти все строковые литералы
      → детект HTML-фрагментов: <[a-zA-Z], </, <>
        → детект JS внутри: <script>, onEvent=, window., document., function()
          → отправить JS-фрагмент в JavaScriptAnalyzer (анализировать изолированно)
            → резолвить найденные символы в .js/.ts-файлах проекта
      → детект JSON: json_encode(...), return {...}
        → распарсить JSON, найти вложенные строки
      → детект CSS: style=, <style>
```

### PHP→JS Bridge (php_js_bridge.py)

```python
@mcp.tool()
def query_php_js_bridge(
    php_file_path: str,
) -> str:
    """Найти в PHP-файле строки, генерирующие JS, и сопоставить их с определениями в .js файлах."""
```

### MCP-инструменты (обновлённые)

```python
@mcp.tool()
def scan_project(root_path: str, language: str | None = None) -> str:
    """Полное сканирование проекта. Если language=None — все поддерживаемые языки."""

@mcp.tool()
def query_function(file_path: str, function_name: str, language: str | None = None) -> str:
    """Сигнатура + тело + callers + callees. language выводится из расширения файла."""

@mcp.tool()
def query_cross_references(symbol_name: str, project_path: str) -> str:
    """Найти все вхождения символа во всех языках проекта (включая PHP→JS bridge)."""
```

## Последствия

### Положительные

1. Cross-language анализ работает в одном процессе — нет latency межпроцессного взаимодействия
2. 70% кода переиспользуется между языками (кэш, обход файлов, MCP-инструменты)
3. Один healthcheck, один деплой, одна запись в `mcp_servers.json`
4. Добавление нового языка — наследование от `BaseAnalyzer` + регистрация в `languages/__init__.py`
5. Go (чистый backend) не требует bridge, но разделяет общую инфраструктуру

### Отрицательные

1. Один процесс = единый point of failure (но это не production-сервис, а dev-инструмент)
2. Все tree-sitter-библиотеки загружаются в один процесс — растёт потребление памяти (оценочно ~50-100 МБ на язык)
3. При добавлении нового языка нужно перезапускать весь сервер
4. Если tree-sitter-go несовместим по версии с остальными — конфликт зависимостей

### Компромиссы

- Если в будущем конфликт зависимостей станет проблемой — Go можно вынести в отдельный сервер (добавить `go-analyzer` в `mcp_servers.json`)
- PHP→JS pipeline можно отключить через флаг конфигурации, если анализ не нужен

## Связанные ADR

- ADR-001: Границы ядра и зоны мутабельности (code_analyzer — autonomous зона)