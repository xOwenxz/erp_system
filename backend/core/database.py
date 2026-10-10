"""Engine, sessão e Base declarativa do SQLAlchemy."""
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.core.config import settings


class Base(DeclarativeBase):
    """Base para todos os modelos ORM."""


def _criar_engine(url: str) -> Engine:
    kwargs: dict = {"echo": settings.database_echo, "pool_pre_ping": True}

    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if url in ("sqlite://", "sqlite:///:memory:"):
            kwargs["poolclass"] = StaticPool  # mesma conexão p/ banco em memória (testes)
        else:
            caminho = url.split("///", 1)[-1]
            Path(caminho).parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(url, **kwargs)

    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _ativar_fk(dbapi_conn, _):  # SQLite não aplica FKs por padrão
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


engine = _criar_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Dependência do FastAPI: abre uma sessão por requisição."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Cria as tabelas (no futuro: substituir por migrações Alembic)."""
    import backend.models  # noqa: F401  (registra os modelos no metadata)

    Base.metadata.create_all(bind=engine)
