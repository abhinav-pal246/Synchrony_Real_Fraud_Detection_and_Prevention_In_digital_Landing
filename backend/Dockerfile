# Pinned to a stable Python (host may run a newer version; the container is what matters)
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /code

# Install dependencies first for better layer caching.
# --retries/--timeout make the large ML wheels (scipy/sklearn) resilient to network blips.
COPY requirements.txt .
RUN pip install --no-cache-dir --retries 10 --timeout 180 -r requirements.txt

# Application code + migrations + ML package + admin scripts
COPY app ./app
COPY ml ./ml
COPY scripts ./scripts
COPY alembic ./alembic
COPY alembic.ini entrypoint.sh ./
RUN chmod +x entrypoint.sh

EXPOSE 8000

# Runs migrations, then launches uvicorn
CMD ["./entrypoint.sh"]
