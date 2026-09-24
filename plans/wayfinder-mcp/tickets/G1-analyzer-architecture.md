# [G1] Архитектура статического анализатора (Tree-sitter)

**Тип**: grilling  
**Статус**: open  
**Метка**: wayfinder:grilling  

## Question

Как спроектировать MCP-сервер статического анализатора на базе Tree-sitter?

Конкретные вопросы:

1. **Что парсить в v1?** Только Python. Какие узлы AST: функции (FunctionDefinition), классы (ClassDefinition), импорты (ImportStatement, ImportFromStatement), вызовы (Call), присваивания (Assignment)?
2. **Формат графа вызовов:** JSON с nodes (id, type, name, file, line) и edges (caller_id, callee_id, type: call/import/inheritance)?
3. **Сигнатуры:** имя, параметры (с type hints), возвращаемый тип, docstring?
4. **MCP-инструменты:** 
   - `scan_project(path)` — полное сканирование проекта, возвращает граф
   - `query_function(name)` — найти функцию и её контекст (сигнатура + тело + кто вызывает + кого вызывает)
   - `query_callers(name)` — кто вызывает функцию
   - `query_callees(name)` — кого вызывает функция
5. **MCP-ресурсы:**
   - `codegraph://summary` — общая статистика (сколько функций, классов, файлов)
   - `codegraph://function/{name}` — детальная информация о функции
6. **Кэширование:** кэшировать AST между запросами? Инвалидация при изменении файлов?

## Блокирует

- Все тикеты по реализации статического анализатора

## Зависимости

- [R1] Исследование Tree-sitter Python API