# [G2] LOG16 v1 API Specification

**Тип**: grilling  
**Статус**: open  
**Метка**: wayfinder:grilling  

## Question

Как спроектировать MCP-сервер LOG16 для v1 (core: MemoryNode + 16 bands + write/query/equalize + status)?

Конкретные вопросы:

1. **MemoryNode:** 
   - id: str (автогенерация)
   - payload: str (сжатый факт)
   - gate_trigger: str (ключевые слова для активации)
   - frequency_band: int (0-15, вычисляется автоматически)
   - access_count: int
   - last_accessed: float (timestamp)
   - metadata: dict (дополнительные поля)
   - recalculate_band(): формула log16(age+1) - log16(access_count+1)

2. **write_to_substrate(payload, gate_trigger):**
   - Создаёт MemoryNode в Band 0 (HF)
   - Если похожий gate_trigger уже есть — увеличивает access_count, пересчитывает band
   - Возвращает node_id

3. **query_substrate(query):**
   - Сканирует gate_triggers (детерминированное совпадение ключевых слов)
   - Band 15 (Core) — всегда возвращается
   - Bands 1-14 — только при совпадении gate_trigger
   - Band 0 — топ-3 последних spike
   - Возвращает отсортированный по band (убывание) список фактов

4. **equalize_memory():**
   - Пересчитывает band для всех узлов
   - Удаляет узлы, упавшие ниже Band 0 (полный decay)
   - Можно вызывать вручную или по расписанию

5. **substrate://status:**
   - Визуализация распределения узлов по 16 band
   - ASCII-диаграмма

6. **Дополнительно:**
   - Нужна ли поддержка семантического поиска (embedding) в v1?
   - Или только keyword match?
   - Какой максимальный размер payload?

## Блокирует

- Все тикеты по реализации LOG16

## Зависимости

- [R2] Исследование первоисточника LOG16/SUBTRAT
- [R3] Исследование FastMCP SDK