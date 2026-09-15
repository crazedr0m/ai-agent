
```python

    # ------------------------------------------------------------------
    # ЭТАП 5: Эволюция промптов при перманентном тупике
    # ------------------------------------------------------------------
    core.console.print(f"[red]❌ Предел попыток исправления кода исчерпан. Запускаем рефлексию над промптом...[/red]")
    
    # 1. Загружаем СИСТЕМНЫЙ промпт Мета-Оптимизатора
    meta_optimizer_system = core.load_prompt_from_file("role_critic_optimizer")
    
    # 2. Загружаем текущий промпт Кодера, который мы хотим улучшить
    current_coder_prompt_text = core.load_prompt_from_file("coder_developer")
    
    # 3. Загружаем ШАБЛОН ЗАПРОСА (User Prompt) Мета-Оптимизатора и подставляем данные
    meta_optimizer_user_template = core.load_prompt_from_file("role_critic_optimizer_user")
    reflector_user_prompt = meta_optimizer_user_template.format(
        current_coder_prompt=current_coder_prompt_text,
        target_code=target_code,
        test_log=test_log
    )
    
    # Вызываем тяжелую рассуждающую модель (например, deepseek-r1:32b) для генерации нового промпта
    suggested_new_prompt = core.call_ollama(meta_optimizer_system, reflector_user_prompt, model_override="deepseek-r1:32b")
    
    # Безопасно обновляем файл prompts/coder_developer.txt через ядро
    if core.update_prompt_in_file("coder_developer", suggested_new_prompt):
        core.console.print("[yellow]🔄 Промпт успешно эволюционировал! Выполняем горячую перезагрузку...[/yellow]")
        core.hot_reload()

```