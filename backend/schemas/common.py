from pydantic import BaseModel, ConfigDict, field_validator


class ORMModel(BaseModel):
    """Base para schemas de saída lidos direto de objetos ORM."""

    model_config = ConfigDict(from_attributes=True)


class EntradaModel(BaseModel):
    """Base para schemas de entrada: remove espaços e converte '' em None."""

    @field_validator("*", mode="before")
    @classmethod
    def _limpar_strings(cls, v):
        if isinstance(v, str):
            v = v.strip()
            return v or None
        return v
