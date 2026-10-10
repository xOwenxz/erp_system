from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models.base import Money, TimestampMixin


class Produto(TimestampMixin, Base):
    __tablename__ = "produtos"

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    nome: Mapped[str] = mapped_column(String(150), index=True)
    categoria: Mapped[str | None] = mapped_column(String(80), index=True)
    preco_custo: Mapped[float] = mapped_column(Money, default=0)
    preco_venda: Mapped[float] = mapped_column(Money, default=0)
    estoque: Mapped[int] = mapped_column(Integer, default=0)
    estoque_minimo: Mapped[int] = mapped_column(Integer, default=0)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    @property
    def estoque_baixo(self) -> bool:
        return (self.estoque or 0) <= (self.estoque_minimo or 0)
