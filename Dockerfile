# 1. Используем официальный облегченный образ Python
FROM python:3.11-slim

# 2. Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# 3. Отключаем буферизацию логов Python (чтобы сразу видеть print() в консоли)
ENV PYTHONUNBUFFERED=1

# 4. Слой зависимостей: копируем только метаданные пакета и исходники,
#    которые нужны setuptools для сборки (для эффективного кэширования слоёв)
COPY pyproject.toml ./
COPY agent.py core_tools.py initializer.py ./
COPY core ./core
COPY agents ./agents
COPY modules ./modules
COPY mcp_servers ./mcp_servers

# 5. Обновляем pip и устанавливаем пакет вместе с зависимостями из pyproject.toml
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

# 6. Копируем оставшийся код приложения в контейнер
COPY . .

# 7. Указываем команду для запуска главного оркестратора
CMD ["python", "agent.py"]
