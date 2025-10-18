FROM python:3.11-slim

WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копируем зависимости и устанавливаем Python-зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY . .

# Копируем start.sh из корня проекта (уровень выше backend)
COPY ../start.sh /start.sh
RUN chmod +x /start.sh

# Открываем порт
EXPOSE 8000

# Переменные окружения
ENV DB_DSN=postgresql+asyncpg://postgres:postgres@postgres:5432/app
ENV APP_DEBUG=false

# Запуск приложения
CMD ["/start.sh"]
