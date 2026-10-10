import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base
from backend.models.base import Money, TimestampMixin

if TYPE_CHECKING:
    from backend.models.cliente import Cliente
    from backend.models.produto import Produto


class StatusVenda(enum.StrEnum):
    CONCLUIDA = "concluida"
    CANCELADA = "cancelada"


class Venda(TimestampMixin, Base):
    __tablename__ = "vendas"

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int | None] = mapped_column(ForeignKey("clientes.id"), index=True)
    data: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    status: Mapped[str] = mapped_column(String(20), default=StatusVenda.CONCLUIDA.value, index=True)
    subtotal: Mapped[float] = mapped_column(Money, default=0)
    desconto: Mapped[float] = mapped_column(Money, default=0)
    total: Mapped[float] = mapped_column(Money, default=0)
    observacao: Mapped[str | None] = mapped_column(String(500))

    cliente: Mapped[Optional["Cliente"]] = relationship(back_populates="vendas")
    itens: Mapped[list["ItemVenda"]] = relationship(
        back_populates="venda", cascade="all, delete-orphan"
    )

    @property
    def cliente_nome(self) -> str | None:
        return self.cliente.nome if self.cliente else None


class ItemVenda(Base):
    __tablename__ = "itens_venda"

    id: Mapped[int] = mapped_column(primary_key=True)
    venda_id: Mapped[int] = mapped_column(ForeignKey("vendas.id", ondelete="CASCADE"), index=True)
    produto_id: Mapped[int] = mapped_column(ForeignKey("produtos.id"), index=True)
    quantidade: Mapped[int] = mapped_column(Integer)
    preco_unitario: Mapped[float] = mapped_column(Money)
    subtotal: Mapped[float] = mapped_column(Money)

    venda: Mapped["Venda"] = relationship(back_populates="itens")
    produto: Mapped["Produto"] = relationship()

    @property
    def produto_nome(self) -> str | None:
        return self.produto.nome if self.produto else None

    @property
    def produto_sku(self) -> str | None:
        return self.produto.sku if self.produto else None
