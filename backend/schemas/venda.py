from datetime import datetime

from pydantic import BaseModel, Field

from backend.schemas.common import EntradaModel, ORMModel


class ItemVendaIn(BaseModel):
    produto_id: int
    quantidade: int = Field(gt=0)
    preco_unitario: float | None = Field(
        default=None, ge=0, description="Se omitido, usa o preço de venda do produto."
    )


class VendaCreate(EntradaModel):
    cliente_id: int | None = None
    data: datetime | None = None
    desconto: float = Field(default=0, ge=0)
    observacao: str | None = Field(default=None, max_length=500)
    itens: list[ItemVendaIn] = Field(min_length=1)


class ItemVendaOut(ORMModel):
    id: int
    produto_id: int
    produto_sku: str | None
    produto_nome: str | None
    quantidade: int
    preco_unitario: float
    subtotal: float


class VendaOut(ORMModel):
    id: int
    cliente_id: int | None
    cliente_nome: str | None
    data: datetime
    status: str
    subtotal: float
    desconto: float
    total: float
    observacao: str | None
    itens: list[ItemVendaOut]
