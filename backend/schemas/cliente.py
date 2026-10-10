from datetime import datetime

from pydantic import Field, field_validator

from backend.core.utils import so_digitos
from backend.schemas.common import EntradaModel, ORMModel


class _ClienteValidacoes(EntradaModel):
    @field_validator("documento", check_fields=False)
    @classmethod
    def _documento(cls, v):
        return so_digitos(v)

    @field_validator("uf", check_fields=False)
    @classmethod
    def _uf(cls, v):
        return v.upper() if v else v

    @field_validator("email", check_fields=False)
    @classmethod
    def _email(cls, v):
        if v and "@" not in v:
            raise ValueError("e-mail inválido")
        return v.lower() if v else v


class ClienteCreate(_ClienteValidacoes):
    nome: str = Field(min_length=2, max_length=150)
    documento: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=150)
    telefone: str | None = Field(default=None, max_length=30)
    cidade: str | None = Field(default=None, max_length=100)
    uf: str | None = Field(default=None, min_length=2, max_length=2)


class ClienteUpdate(_ClienteValidacoes):
    nome: str | None = Field(default=None, min_length=2, max_length=150)
    documento: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=150)
    telefone: str | None = Field(default=None, max_length=30)
    cidade: str | None = Field(default=None, max_length=100)
    uf: str | None = Field(default=None, min_length=2, max_length=2)
    ativo: bool | None = None


class ClienteOut(ORMModel):
    id: int
    nome: str
    documento: str | None
    email: str | None
    telefone: str | None
    cidade: str | None
    uf: str | None
    ativo: bool
    criado_em: datetime
