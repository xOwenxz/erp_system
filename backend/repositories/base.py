"""Repositório genérico: concentra o acesso a dados (queries) de cada entidade."""
from collections.abc import Iterable
from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.database import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, db: Session):
        self.db = db

    def get(self, id_: int) -> ModelT | None:
        return self.db.get(self.model, id_)

    def list(self, *, filtros: Iterable = (), skip: int = 0, limit: int = 100, ordem=None) -> list[ModelT]:
        stmt = select(self.model).where(*filtros)
        stmt = stmt.order_by(ordem if ordem is not None else self.model.id)
        return list(self.db.scalars(stmt.offset(skip).limit(limit)))

    def add(self, obj: ModelT) -> ModelT:
        self.db.add(obj)
        self.db.flush()
        return obj

    def update(self, obj: ModelT, valores: dict[str, Any]) -> ModelT:
        """Aplica alterações ignorando None em colunas NOT NULL."""
        colunas = self.model.__table__.c
        for campo, valor in valores.items():
            if valor is None and campo in colunas and not colunas[campo].nullable:
                continue
            setattr(obj, campo, valor)
        self.db.flush()
        return obj

    def delete(self, obj: ModelT) -> None:
        self.db.delete(obj)
        self.db.flush()
