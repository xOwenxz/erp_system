"""Tipos e mixins compartilhados pelos modelos."""
from datetime import datetime

from sqlalchemy import DateTime, Numeric
from sqlalchemy.orm import Mapped, mapped_column

# Valores monetários: NUMERIC(14,2) no banco, float no Python.
Money = Numeric(14, 2, asdecimal=False)


class TimestampMixin:
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )
