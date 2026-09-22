"""Database engine, session factory, and FastAPI dependency."""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import SQLALCHEMY_DATABASE_URL

engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

Base = declarative_base()


def get_db():
    """Yield a database session, closing it afterwards (FastAPI dependency)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
