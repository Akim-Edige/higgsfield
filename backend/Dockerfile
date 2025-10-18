FROM python:3.11-slim

WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей из backend/
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Копируем всё приложение
COPY backend/ /app/

# Делаем стартовый скрипт исполняемым
RUN chmod +x /app/start.sh

# Переменные окружения по умолчанию
ENV PYTHONPATH=/app
ENV DB_DSN=${DB_DSN}
ENV APP_DEBUG=false

EXPOSE 8000

CMD ["/app/start.sh"]
