"""Central configuration, read from environment variables."""

import os


def _to_sqlalchemy_url(url: str) -> str:
    """SQLAlchemy needs an explicit driver; we use psycopg (v3)."""
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://synchrony:synchrony@postgres:5432/synchrony"
)
SQLALCHEMY_DATABASE_URL = _to_sqlalchemy_url(DATABASE_URL)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
