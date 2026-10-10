from datetime import date
from typing import Any, Literal

from pydantic import BaseModel

Agrupamento = Literal["dia", "semana", "mes"]


# ---------- Dashboard ----------
class KPIs(BaseModel):
    faturamento: float
    qtd_vendas: int
    ticket_medio: float
    lucro_bruto: float
    margem_bruta: float  # %
    itens_vendidos: int
    clientes_ativos: int
    valor_estoque: float
    produtos_estoque_baixo: int


class PontoSerie(BaseModel):
    periodo: date
    faturamento: float
    qtd_vendas: int


class ItemRanking(BaseModel):
    id: int | None
    nome: str
    quantidade: float
    valor: float


class ItemCategoria(BaseModel):
    categoria: str
    valor: float


class ItemEstoqueBaixo(BaseModel):
    id: int
    sku: str
    nome: str
    estoque: int
    estoque_minimo: int


class DashboardOut(BaseModel):
    periodo_inicio: date | None
    periodo_fim: date | None
    agrupamento: Agrupamento
    kpis: KPIs
    vendas_por_periodo: list[PontoSerie]
    top_produtos: list[ItemRanking]
    top_clientes: list[ItemRanking]
    vendas_por_categoria: list[ItemCategoria]
    estoque_baixo: list[ItemEstoqueBaixo]


# ---------- Relatórios ----------
class RelatorioInfo(BaseModel):
    nome: str
    titulo: str
    descricao: str
    usa_periodo: bool


class RelatorioDados(BaseModel):
    nome: str
    titulo: str
    colunas: list[str]
    linhas: list[dict[str, Any]]
    total_linhas: int


# ---------- Excel ----------
class ColunaPerfil(BaseModel):
    nome: str
    tipo: str
    nao_nulos: int
    nulos: int
    unicos: int
    exemplo: Any = None


class ExcelAnaliseOut(BaseModel):
    arquivo: str
    abas: list[str]
    aba: str
    total_linhas: int
    total_colunas: int
    colunas: list[ColunaPerfil]
    estatisticas: dict[str, dict[str, Any]]
    dados: list[dict[str, Any]]
    truncado: bool


class CampoImportacaoOut(BaseModel):
    nome: str
    tipo: str
    obrigatorio: bool
    aliases: list[str]


class EntidadeImportacaoOut(BaseModel):
    entidade: str
    campos: list[CampoImportacaoOut]


class ImportErro(BaseModel):
    linha: int
    erro: str


class ImportResultado(BaseModel):
    entidade: str
    total_linhas: int = 0
    inseridos: int = 0
    atualizados: int = 0
    erros: list[ImportErro] = []
