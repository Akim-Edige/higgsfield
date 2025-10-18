FROM python:3.11-slim

WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копируем зависимости из backend и устанавливаем их
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Копируем всё содержимое backend/
COPY backend/ /app/

# Делаем start.sh исполняемым
RUN chmod +x /app/start.sh

EXPOSE 8000

CMD ["/app/start.sh"]
