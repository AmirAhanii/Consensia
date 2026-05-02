from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session


def normalize_postgres_url(url: str) -> str:
    """Render and Heroku often use postgres:// or postgresql:// without a driver; we use psycopg3 only."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


_raw_db_url = os.getenv("DATABASE_URL", "").strip()
DATABASE_URL = (
    normalize_postgres_url(_raw_db_url)
    if _raw_db_url
    else "postgresql+psycopg://consensia:consensia_password@db:5432/consensia"
)


def _with_connect_timeout(url: str, seconds: int = 10) -> str:
    if "connect_timeout=" in url:
        return url
    joiner = "&" if "?" in url else "?"
    return f"{url}{joiner}connect_timeout={seconds}"


class Base(DeclarativeBase):
    pass


engine = create_engine(
    _with_connect_timeout(DATABASE_URL),
    echo=True,
    pool_pre_ping=True,
    pool_timeout=30,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()