FROM python:3.10-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода бота
COPY main.py .

# Создание директории для базы данных
RUN mkdir -p /data

# Переменные окружения
ENV TOKEN=     DB_PATH=/data/practicum.db

# Volume для сохранения базы данных
VOLUME /data

# Запуск бота
CMD ["python", "main.py"]
