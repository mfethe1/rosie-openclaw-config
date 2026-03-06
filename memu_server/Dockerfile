FROM python:3.11-slim

WORKDIR /app

COPY server.py /app/server.py

# Persist memU sqlite + WAL on Railway volume when mounted
RUN mkdir -p /app/data/memu_store

ENV PYTHONUNBUFFERED=1 \
    MEMU_MEMORY_DIR=/app/data \
    MEMU_BIND_HOST=0.0.0.0 \
    MEMU_ALLOW_PUBLIC_BIND=1 \
    MEMU_TTL_DAYS=180

EXPOSE 8080

CMD ["python", "/app/server.py"]
