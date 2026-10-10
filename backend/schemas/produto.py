from datetime import datetime

from pydantic import Field

from backend.schemas.common import EntradaModel, ORMModel


class ProdutoCreate(EntradaModel):
    sku: str = Field(min_length=1, max_length=50)
    nome: str = Field(min_length=2, max_length=150)
    categoria: str | None = Field(default=None, max_length=80)
    preco_custo: float = Field(default=0, ge=0)
    preco_venda: float = Field(ge=0)
    estoque: int = Field(default=0, ge=0)
    estoque_minimo: int = Field(default=0, ge=0)


class ProdutoUpdate(EntradaModel):
    sku: str | None = Field(default=None, min_length=1, max_length=50)
    nome: str | None = Field(default=None, min_length=2, max_length=150)
    categoria: str | None = Field(default=None, max_length=80)
    preco_custo: float | None = Field(default=None, ge=0)
    preco_venda: float | None = Field(default=None, ge=0)
    estoque: int | None = Field(default=None, ge=0)
    estoque_minimo: int | None = Field(default=None, ge=0)
    ativo: bool | None = None


class ProdutoOut(ORMModel):
    id: int
    sku: str
    nome: str
    categoria: str | None
    preco_custo: float
    preco_venda: float
    estoque: int
    estoque_minimo: int
    estoque_baixo: bool
    ativo: bool
    criado_em: datetime
