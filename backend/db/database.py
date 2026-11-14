"""Database engine, sessions, and company-scoped lookups.

The engine is created on first use, so importing this module needs neither
DATABASE_URL nor a database driver. The URL comes from the environment
(backend/.env locally, the host's secret settings when deployed) and is never
logged or committed.
"""

import os
from collections.abc import Iterator
from functools import lru_cache
from typing import TypeVar

from sqlalchemy import Engine, event
from sqlmodel import Session, SQLModel, create_engine, select

from .models import TENANT_MODELS

ModelT = TypeVar("ModelT", bound=SQLModel)


def normalize_database_url(url: str) -> str:
    """Name the PostgreSQL driver (psycopg 3) instead of relying on a default.

    Supabase shows postgres:// connection strings. postgres:// and plain
    postgresql:// become postgresql+psycopg://. A URL that already names a
    driver (postgresql+psycopg2://) and any other database (sqlite://) are
    returned unchanged. The URL is never logged.
    """
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url.removeprefix(prefix)
    return url


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set. Add it to backend/.env; never commit it.")
    return normalize_database_url(url)


def _enforce_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    # SQLite ignores foreign keys unless each connection turns them on.
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    # SQL echo prints statement values (emails, token hashes), so it is opt-in.
    engine = create_engine(
        _database_url(),
        echo=os.environ.get("SQL_ECHO") == "1",
        pool_pre_ping=True,
    )
    if engine.dialect.name == "sqlite":
        event.listen(engine, "connect", _enforce_sqlite_foreign_keys)
    return engine


def create_db_and_tables() -> None:
    """Create missing tables in an empty local or test database.

    This never alters an existing table. The shared Supabase database is
    changed only by the SQL files in backend/db/migrations/.
    """
    SQLModel.metadata.create_all(get_engine())


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session


def company_select(model: type[ModelT], company_id: int):
    """Start a query for one company's rows of a tenant table.

    Build every tenant query from this so the company filter cannot be left
    out. The company comes from the caller's verified token, never from the app.
    """
    if model not in TENANT_MODELS:
        raise TypeError(f"{model.__name__} is not a tenant table")
    return select(model).where(model.company_id == company_id)


def get_in_company(
    session: Session, model: type[ModelT], company_id: int, record_id: int
) -> ModelT | None:
    """Return the row with this id only if it belongs to the company."""
    return session.exec(company_select(model, company_id).where(model.id == record_id)).first()
