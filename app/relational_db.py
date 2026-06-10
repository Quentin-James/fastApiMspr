from __future__ import annotations

from sqlalchemy import URL, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings


def _build_engine_url():
    """
    Supabase pooler requires username 'postgres.<ref>' which contains a dot.
    SQLAlchemy URL.create() handles this correctly unlike plain string URLs.
    Falls back to the raw string for non-Supabase/local connections.
    """
    raw = settings.mysql_database_url
    if "pooler.supabase.com" in raw:
        from urllib.parse import urlparse
        p = urlparse(raw)
        return URL.create(
            drivername=p.scheme,
            username=p.username,
            password=p.password,
            host=p.hostname,
            port=p.port,
            database=p.path.lstrip("/"),
        )
    return raw


engine = create_engine(
    _build_engine_url(),
    future=True,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,
)

Base = declarative_base()


def init_relational_db() -> None:
    from app.models.account import Base as AccountBase

    AccountBase.metadata.create_all(bind=engine)


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
