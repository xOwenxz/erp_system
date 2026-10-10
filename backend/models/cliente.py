from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base
from backend.models.base import TimestampMixin

if TYPE_CHECKING:
    from backend.models.venda import Venda


class Cliente(TimestampMixin, Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(150), index=True)
    documento: Mapped[str | None] = mapped_column(String(20), unique=True)  # CPF/CNPJ (só dígitos)
    email: Mapped[str | None] = mapped_column(String(150), index=True)
    telefone: Mapped[str | None] = mapped_column(String(30))
    cidade: Mapped[str | None] = mapped_column(String(100))
    uf: Mapped[str | None] = mapped_column(String(2))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    vendas: Mapped[list["Venda"]] = relationship(back_populates="cliente")
