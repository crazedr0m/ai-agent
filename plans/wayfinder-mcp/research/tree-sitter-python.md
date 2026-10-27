# Tree-sitter Python API — Research Results

**Тикет**: [R1](../tickets/R1-tree-sitter-research.md)
**Статус**: closed → resolved
**Дата**: 2026-10-27

## Установка

```bash
pip install tree-sitter tree-sitter-python
```

Версии: `tree-sitter==0.26.0`, `tree-sitter-python==0.25.0`

## Как загрузить грамматику Python и получить AST

```python
from tree_sitter import Language, Parser
import tree_sitter_python

LANGUAGE = Language(tree_sitter_python.language())
parser = Parser(LANGUAGE)

code = "def hello(name: str) -> str:\n    return f'Hello {name}'"
tree = parser.parse(bytes(code, 'utf-8'))
root = tree.root_node  # module
```

## Ключевые типы узлов AST

| Тип узла | Что представляет |
|----------|-----------------|
| `function_definition` | `def name(...):` |
| `class_definition` | `class Name:` |
| `import_statement` | `import os` |
| `import_from_statement` | `from typing import Optional` |
| `call` | `func(...)` — вызов функции |
| `assignment` | `x = 1` |
| `identifier` | Имя переменной/функции/класса |
| `parameters` | Список параметров функции |
| `typed_parameter` | `name: type` |
| `return_statement` | `return ...` |
| `decorated_definition` | `@decorator\ndef ...` |
| `string` / `string_content` | Строковые литералы и docstring |

## Как извлечь функции, классы, импорты, вызовы

```python
def collect_definitions(root, code):
    result = {'functions': [], 'classes': [], 'imports': [], 'calls': []}
    
    def walk(node):
        if node.type == 'function_definition':
            name = node.child_by_field_name('name')
            result['functions'].append({
                'name': code[name.start_byte:name.end_byte],
                'start': node.start_point,
                'end': node.end_point
            })
        elif node.type == 'class_definition':
            name = node.child_by_field_name('name')
            result['classes'].append({
                'name': code[name.start_byte:name.end_byte],
                'start': node.start_point,
                'end': node.end_point
            })
        elif node.type == 'import_statement':
            result['imports'].append(code[node.start_byte:node.end_byte])
        elif node.type == 'call':
            func = node.child_by_field_name('function')            if func:                result['calls'].append(code[func.start_byte:func.end_byte])
        for child in node.children:
            walk(child)
    
    walk(root)
    return result
```

## Как извлечь сигнатуры функций

```python
def get_function_signature(node, code):
    """Извлечь сигнатуру функции из function_definition node."""
    name_node = node.child_by_field_name('name')
    params_node =node.child_by_field_name('parameters')
    return_type_node = node.child_by_field_name('return_type')
    
    name = code[name_node.start_byte:name_node.end_byte]
    
    params = []
    if params_node:
        for child in params_node.children:
            if child.type == 'typed_parameter':
                param_name = child.child_by_field_name('name')
                param_type = child.child_by_field_name('type')
                params.append({
                    'name': code[param_name.start_byte: param_name.end_byte],
                    'type': code[param_type.start_byte: param_type.end_byte] if param_type else None
                })
            elif child.type == 'identifier':
                params.append({
                    'name': code[child.start_byte: child.end_byte],
                    'type': None
                })
    
    return_type = None
    if return_type_node:
        return_type = code[return_type_node.start_byte: return_type_node.end_byte]
    
    # Docstring
    body = node.child_by_field_name('body')
    docstring = None
    if body and body.children:
        first =body.children[0]
        if first.type == 'expression_statement' and first.children:
            expr = first.children[0]
            if expr.type == 'string':
                docstring = code[expr.start_byte:expr.end_byte].strip('"\'')
    
    return {
        'name': name,
        'params': params,
        'return_type': return_type,
        'docstring': docstring
    }
```

## Построение графа вызовов

```python
def build_call_graph(tree, code):
    """Построить граф вызовов: {caller: [callee, ...]}"""
    graph = {}
    
    def walk(node, current_function=None):
        if node.type == 'function_definition':
            name_node = node.child_by_field_name('name')
            current_function = code[name_node.start_byte:name_node.end_byte]
            graph[current_function] = []
        
        if node.type == 'call' and current_function:
            func_node = node.child_by_field_name('function')
            if func_node:
                callee = code[func_node.start_byte:func_node.end_byte]
                graph[current_function].append(callee)
        
        for child in node.children:
            walk(child, current_function)
    
    walk(root)
    return graph
```

## Ограничения Tree-sitter

1. **Только синтаксис, не семантика** — не знает, что `print` — встроенная функция
2. **Не разрешает импорты** — не может сказать, что `Optional` из `typing`
3. **call может быть любым** — `foo()`, `obj.method()`, `module.func()` — все `call`
4. **Не знает перегрузки** — не отличает `def f(x: int)` от `def f(x: str)`
5. **Не проверяет типы** — не знает, что `x + 1` валиднодля `int`

Эти ограичения означают, что граф вызовов — это только "кто каквываеся по имени", без разрешения импортов и псевдонимов.

## Альтернативы

- **`tree-sitter-languages`** — пакет-обёртка для быстрого доступа к `get_language('python')`, но необязателен
- **`libcst`** — Instagram's CST parser для Python, более "Pythonic" API, но только Python
- **`ast`** — стандартный модуль Python, не требует установки, но нет поддержки грамматик для других языков

Для v1 используем Tree-sitter (уже установлен), так как он поддерживает множество языков и даёт точные позиции в исходном коде.