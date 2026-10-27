# -*- coding: utf-8 -*-
# modules/repo_map.py — Карта репозитория на базе анализатора (Фаза 6.1)
#
# Строит структурированную карту проекта, альтернатива scan_legacy_project():
# - scan_legacy_project() читает первые 50 строк каждого файла
# - build_repo_map() использует AST-анализатор для точной карты
#
# Возвращает JSON с:
#   summary        — статистика (файлы, функции, классы, размер)
#   file_index     — для каждого файла: функции, классы, размер, строки
#   call_graph     — кто кого вызывает {caller: [callees]}
#   import_graph   — кто от кого зависит {file: [imported_files]}
#   file_sizes     — размер и строка на файл

import json
import os
from typing import Optional

from mcp_servers.code_analyzer.languages import (
    get_analyzer,
    get_supported_languages,
    infer_language,
)
from mcp_servers.code_analyzer.core import _get_all_files, _clear_cache


# ── Расширения языков ──────────────────────────────────────────────

_LANG_EXT: dict[str, str] = {
    "python": ".py",
    "php": ".php",
    "javascript": ".js",
    "typescript": ".ts",
    "go": ".go",
}


def _resolve_import_to_file(import_stmt: str, project_root: str) -> list[str]:
    """Попытаться превратить import-statement в список файлов проекта.

    Работает приблизительно — по ключевым словам в import'е ищет
    файлы, содержащие эти слова в пути.
    """
    # Извлекаем имена модулей из import statement
    stmt = import_stmt.strip()
    candidates = set()

    # from X import Y → X, Y
    # import X.Y.Z → X, X/Y, X/Y/Z
    parts = stmt.replace("from ", "").replace("import ", "").split()
    for p in parts:
        p = p.strip().rstrip(",").rstrip(";")
        if not p or p in ("as",):
            continue
        # Пробуем разные варианты путей
        segments = p.split(".")
        for i in range(1, len(segments) + 1):
            partial = "/".join(segments[:i])
            for ext in (".py", ".php", ".js", ".ts", ".go"):
                # Прямой путь
                full = os.path.join(project_root, f"{partial}{ext}")
                if os.path.isfile(full):
                    candidates.add(os.path.relpath(full, project_root))
                # Путь с __init__
                init_full = os.path.join(project_root, partial, f"__init__{ext}")
                if os.path.isfile(init_full):
                    candidates.add(os.path.relpath(init_full, project_root))

    return sorted(candidates)


def build_repo_map(
    root_path: str,
    language: Optional[str] = None,
    skip_dirs: Optional[list[str]] = None,
) -> dict:
    """Построить структурированную карту репозитория.

    Args:
        root_path: корневая директория проекта
        language: язык сканирования (None = все поддерживаемые)
        skip_dirs: директории для пропуска (по умолч. venv, .git, __pycache__)

    Returns:
        dict с полями summary, file_index, call_graph, import_graph, file_sizes
    """
    if not os.path.isdir(root_path):
        return {"error": f"Директория '{root_path}' не найдена"}

    _clear_cache()

    skip = set(skip_dirs or ["venv", ".git", "__pycache__", "node_modules", "vendor", ".pytest_cache"])

    if language:
        languages_to_scan = [language]
    else:
        languages_to_scan = get_supported_languages()

    # ── Сбор данных по языкам ──────────────────────────────────────
    file_index: dict[str, list[dict]] = {}       # rel_path → [functions]
    file_classes: dict[str, list[dict]] = {}      # rel_path → [classes]
    file_imports: dict[str, list[str]] = {}        # rel_path → [import statements]
    file_sizes: dict[str, dict] = {}               # rel_path → {bytes, lines}
    call_graph: dict[str, list[str]] = {}           # function_name → [callees]
    all_functions: list[dict] = []

    for lang in languages_to_scan:
        analyzer = get_analyzer(lang)
        if analyzer is None:
            continue

        ext = _LANG_EXT.get(lang, ".txt")
        files = _get_all_files(root_path, extension=ext)

        for fp in files:
            rel = os.path.relpath(fp, root_path)

            # Проверяем skip-директории
            if any(f"/{sd}/" in f"/{rel}/" or rel.startswith(f"{sd}/") for sd in skip):
                continue

            # Размер файла
            try:
                stat = os.stat(fp)
                with open(fp, "r", encoding="utf-8", errors="replace") as fh:
                    num_lines = sum(1 for _ in fh)
                file_sizes[rel] = {
                    "bytes": stat.st_size,
                    "lines": num_lines,
                }
            except Exception:
                file_sizes[rel] = {"bytes": 0, "lines": 0}

            defs = analyzer.collect_definitions(fp)

            # Функции
            funcs = []
            for fn in defs["functions"]:
                fn["file"] = rel
                fn["language"] = lang
                funcs.append(fn)
                all_functions.append(fn)

            if funcs:
                file_index[rel] = funcs

            # Классы
            classes = []
            for cls in defs["classes"]:
                cls["file"] = rel
                cls["language"] = lang
                classes.append(cls)
            if classes:
                file_classes[rel] = classes

            # Импорты
            if defs["imports"]:
                file_imports[rel] = defs["imports"]

            # Граф вызовов для этого файла
            fg = analyzer.build_call_graph(fp)
            for caller, callees in fg.items():
                if caller not in call_graph:
                    call_graph[caller] = []
                for c in callees:
                    if c not in call_graph[caller]:
                        call_graph[caller].append(c)

    # ── Строим import_graph ──────────────────────────────────────────
    import_graph: dict[str, list[str]] = {}
    for rel, imports in file_imports.items():
        resolved = []
        for imp in imports:
            resolved.extend(_resolve_import_to_file(imp, root_path))
        if resolved:
            import_graph[rel] = sorted(set(resolved))

    # ── Сводка ─────────────────────────────────────────────────────
    total_bytes = sum(fs["bytes"] for fs in file_sizes.values())
    total_lines = sum(fs["lines"] for fs in file_sizes.values())

    summary = {
        "files_scanned": len(file_sizes),
        "total_functions": len(all_functions),
        "total_classes": sum(len(cls) for cls in file_classes.values()),
        "total_bytes": total_bytes,
        "total_lines": total_lines,
        "languages": languages_to_scan,
        "files_with_functions": len(file_index),
        "files_with_classes": len(file_classes),
        "files_with_imports": len(file_imports),
    }

    # ── Топ-10 самых больших файлов ────────────────────────────────
    top_files = sorted(file_sizes.items(), key=lambda x: x[1]["lines"], reverse=True)[:10]
    largest_files = [
        {"file": rel, "lines": info["lines"], "bytes": info["bytes"]}
        for rel, info in top_files
    ]

    # ── Упрощённая карта для LLM (только имена функций по файлам) ──
    file_summary: dict[str, dict] = {}
    for rel in sorted(file_sizes):
        entry = {
            "lines": file_sizes.get(rel, {}).get("lines", 0),
            "functions": [fn["name"] for fn in file_index.get(rel, [])],
            "classes": [cls["name"] for cls in file_classes.get(rel, [])],
            "imports": len(file_imports.get(rel, [])),
            "language": infer_language(rel) or "unknown",
        }
        file_summary[rel] = entry

    result = {
        "summary": summary,
        "largest_files": largest_files,
        "file_summary": file_summary,
        "file_sizes": file_sizes,
        "call_graph": call_graph,
        "import_graph": import_graph,
    }

    return result


def format_repo_map_for_llm(repo_map: dict, max_files: int = 50) -> str:
    """Отформатировать карту репозитория в компактный текст для LLM.

    Args:
        repo_map: результат build_repo_map()
        max_files: макс. количество файлов в текстовой карте

    Returns:
        строка с картой проекта, пригодная для подачи в промпт
    """
    if "error" in repo_map:
        return f"Ошибка: {repo_map['error']}"

    lines = []
    s = repo_map["summary"]
    lines.append(f"📊 Проект: {s['files_scanned']} файлов, {s['total_lines']} строк, "
                 f"{s['total_functions']} функций, {s['total_classes']} классов")
    lines.append(f"   Языки: {', '.join(s['languages'])}")
    lines.append(f"   Всего: {s['total_bytes']:,} байт")
    lines.append("")

    # Крупные файлы
    if repo_map.get("largest_files"):
        lines.append("🔍 Крупнейшие файлы:")
        for lf in repo_map["largest_files"][:5]:
            lines.append(f"   {lf['file']} — {lf['lines']} строк, {lf['bytes']:,} байт")
        lines.append("")

    # Карта файлов
    file_summary = repo_map.get("file_summary", {})
    shown = 0
    for rel in sorted(file_summary):
        if shown >= max_files:
            remaining = len(file_summary) - shown
            lines.append(f"... и ещё {remaining} файлов")
            break
        shown += 1
        info = file_summary[rel]
        funcs = info["functions"][:8]  # не более 8 функций в строке
        classes = info["classes"][:4]

        parts = [f"📄 {rel} ({info['lines']} строк, {info['language']})"]
        if classes:
            parts.append(f"   🏷️ Классы: {', '.join(classes)}")
        if funcs:
            parts.append(f"   ⚙️ Функции: {', '.join(funcs)}")
            if len(info["functions"]) > 8:
                parts[-1] += f" [+{len(info['functions']) - 8}]"
        if info["imports"] > 0:
            parts.append(f"   📦 Импортов: {info['imports']}")
        lines.extend(parts)

    lines.append("")

    # Граф вызовов (только топ)
    call_graph = repo_map.get("call_graph", {})
    if call_graph:
        lines.append("🔗 Граф вызовов (первые 30):")
        # Сортируем по количеству callees, самые связанные сверху
        sorted_calls = sorted(call_graph.items(), key=lambda x: len(x[1]), reverse=True)
        for caller, callees in sorted_calls[:30]:
            callee_str = ", ".join(callees[:5])
            if len(callees) > 5:
                callee_str += f" [+{len(callees) - 5}]"
            lines.append(f"   {caller} → {callee_str}")

    return "\n".join(lines)


def format_dependency_map(repo_map: dict) -> str:
    """Отформатировать граф зависимостей (import_graph) для LLM.

    Показывает, какие файлы от каких зависят — основа для
    планирования порядка миграции.
    """
    import_graph = repo_map.get("import_graph", {})
    if not import_graph:
        return "Граф импортов пуст."

    lines = ["📦 Граф зависимостей (imports):"]
    for rel in sorted(import_graph):
        deps = import_graph[rel]
        if deps:
            dep_str = ", ".join(deps[:5])
            if len(deps) > 5:
                dep_str += f" [+{len(deps) - 5}]"
            lines.append(f"   {rel} → {dep_str}")

    # Листья (файлы, которые ничего не импортируют)
    file_summary = repo_map.get("file_summary", {})
    leaves = [rel for rel in file_summary if rel not in import_graph or not import_graph[rel]]
    if leaves:
        lines.append(f"\n🍃 Листья (нет зависимостей):")
        for leaf in leaves[:20]:
            lines.append(f"   {leaf}")

    return "\n".join(lines)