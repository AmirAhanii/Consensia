from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://consensia:consensia_password@db:5432/consensia",
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