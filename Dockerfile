# 1. Используем официальный облегченный образ Python
FROM python:3.11-slim

# 2. Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# 3. Отключаем буферизацию логов Python (чтобы сразу видеть print() в консоли)
ENV PYTHONUNBUFFERED=1

# 4. Сначала копируем только файл зависимостей (для эффективного кэширования слоев Docker)
COPY requirements.txt .

# 5. Обновляем pip и устанавливаем зависимости
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 6. Копируем оставшийся код приложения в контейнер
COPY . .

# 7. Указываем команду для запуска приложения (замените app.py на ваш главный файл)
CMD ["python", "app.py"]
