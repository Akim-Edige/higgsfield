FROM python:3.11-slim

WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копируем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код проекта
COPY . .

# Настройка базы данных
RUN mkdir -p /var/lib/postgresql/data && chown -R postgres:postgres /var/lib/postgresql
USER postgres
RUN /usr/lib/postgresql/*/bin/initdb -D /var/lib/postgresql/data
USER root

COPY start.sh /start.sh
RUN chmod +x /start.sh

ENV DB_DSN=postgresql+asyncpg://postgres:postgres@localhost:5432/app
ENV APP_DEBUG=false

EXPOSE 8000
CMD ["/start.sh"]
