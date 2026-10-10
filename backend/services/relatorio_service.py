"""Relatórios baseados em um registro (registry).

Para criar um novo relatório basta escrever uma função que retorne um DataFrame
e decorá-la com @relatorio(...). Ele aparece automaticamente na API e na tela.
"""
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd
from sqlalchemy import Float, func, select, type_coerce
from sqlalchemy.orm import Session

from backend.core.exceptions import NotFoundError
from backend.core.utils import filtro_periodo
from backend.models import Cliente, ItemVenda, Produto, StatusVenda, Venda

Gerador = Callable[[Session, date | None, date | None], pd.DataFrame]


@dataclass(frozen=True)
class DefinicaoRelatorio:
    nome: str
    titulo: str
    descricao: str
    usa_periodo: bool
    gerador: Gerador


_REGISTRO: dict[str, DefinicaoRelatorio] = {}


def relatorio(nome: str, titulo: str, descricao: str, usa_periodo: bool = True):
    def decorador(func: Gerador) -> Gerador:
        _REGISTRO[nome] = DefinicaoRelatorio(nome, titulo, descricao, usa_periodo, func)
        return func
    return decorador


def _df(db: Session, stmt, colunas: list[str]) -> pd.DataFrame:
    return pd.DataFrame(db.execute(stmt).all(), columns=colunas)


def _float(expr):
    return type_coerce(expr, Float)


# ----------------------------------------------------------------------------
# Relatórios disponíveis
# ----------------------------------------------------------------------------
@relatorio("vendas", "Vendas por período",
           "Todas as vendas (concluídas e canceladas) do período, com cliente e valores.")
def rel_vendas(db: Session, inicio: date | None, fim: date | None) -> pd.DataFrame:
    qtd_itens = (select(func.coalesce(func.sum(ItemVenda.quantidade), 0))
                 .where(ItemVenda.venda_id == Venda.id).correlate(Venda).scalar_subquery())
    stmt = (select(Venda.id, Venda.data, Cliente.nome, Venda.status, qtd_itens,
                   Venda.subtotal, Venda.desconto, Venda.total)
            .outerjoin(Cliente, Venda.cliente_id == Cliente.id)
            .where(*filtro_periodo(Venda.data, inicio, fim))
            .order_by(Venda.data))
    df = _df(db, stmt, ["Venda", "Data", "Cliente", "Status", "Itens", "Subtotal", "Desconto", "Total"])
    df["Cliente"] = df["Cliente"].fillna("Consumidor final")
    df["Status"] = df["Status"].str.capitalize()
    return df


@relatorio("itens_vendidos", "Itens vendidos",
           "Detalhamento item a item das vendas concluídas no período.")
def rel_itens(db: Session, inicio: date | None, fim: date | None) -> pd.DataFrame:
    stmt = (select(Venda.id, Venda.data, Cliente.nome, Produto.sku, Produto.nome, Produto.categoria,
                   ItemVenda.quantidade, ItemVenda.preco_unitario, ItemVenda.subtotal)
            .select_from(ItemVenda)
            .join(Venda, ItemVenda.venda_id == Venda.id)
            .join(Produto, ItemVenda.produto_id == Produto.id)
            .outerjoin(Cliente, Venda.cliente_id == Cliente.id)
            .where(Venda.status == StatusVenda.CONCLUIDA.value, *filtro_periodo(Venda.data, inicio, fim))
            .order_by(Venda.data, Venda.id))
    df = _df(db, stmt, ["Venda", "Data", "Cliente", "SKU", "Produto", "Categoria",
                        "Quantidade", "Preço unitário", "Subtotal"])
    df["Cliente"] = df["Cliente"].fillna("Consumidor final")
    return df


@relatorio("produtos_mais_vendidos", "Curva de produtos (mais vendidos)",
           "Quantidade, faturamento e lucro estimado por produto no período.")
def rel_produtos(db: Session, inicio: date | None, fim: date | None) -> pd.DataFrame:
    faturamento = _float(func.sum(ItemVenda.subtotal))
    stmt = (select(Produto.sku, Produto.nome, Produto.categoria, func.sum(ItemVenda.quantidade),
                   faturamento, _float(func.sum(ItemVenda.quantidade * Produto.preco_custo)))
            .select_from(ItemVenda)
            .join(Venda, ItemVenda.venda_id == Venda.id)
            .join(Produto, ItemVenda.produto_id == Produto.id)
            .where(Venda.status == StatusVenda.CONCLUIDA.value, *filtro_periodo(Venda.data, inicio, fim))
            .group_by(Produto.id, Produto.sku, Produto.nome, Produto.categoria)
            .order_by(faturamento.desc()))
    df = _df(db, stmt, ["SKU", "Produto", "Categoria", "Quantidade", "Faturamento", "Custo estimado"])
    df["Lucro estimado"] = (df["Faturamento"] - df["Custo estimado"]).round(2)
    total = df["Faturamento"].sum()
    df["% Faturamento"] = (df["Faturamento"] / total * 100).round(2) if total else 0.0
    df["% Acumulado"] = df["% Faturamento"].cumsum().round(2) if total else 0.0
    return df


@relatorio("clientes", "Compras por cliente",
           "Número de compras, total comprado, ticket médio e última compra de cada cliente.")
def rel_clientes(db: Session, inicio: date | None, fim: date | None) -> pd.DataFrame:
    sub = (select(Venda.cliente_id,
                  func.count(Venda.id).label("compras"),
                  _float(func.sum(Venda.total)).label("total"),
                  func.max(Venda.data).label("ultima"))
           .where(Venda.status == StatusVenda.CONCLUIDA.value, *filtro_periodo(Venda.data, inicio, fim))
           .group_by(Venda.cliente_id).subquery())
    total = func.coalesce(sub.c.total, 0.0)
    stmt = (select(Cliente.nome, Cliente.documento, Cliente.email, Cliente.cidade, Cliente.uf,
                   func.coalesce(sub.c.compras, 0), total, sub.c.ultima)
            .outerjoin(sub, sub.c.cliente_id == Cliente.id)
            .where(Cliente.ativo.is_(True))
            .order_by(total.desc()))
    df = _df(db, stmt, ["Cliente", "Documento", "E-mail", "Cidade", "UF",
                        "Nº compras", "Total comprado", "Última compra"])
    df["Ticket médio"] = np.where(df["Nº compras"] > 0,
                                  df["Total comprado"] / df["Nº compras"].replace(0, 1), 0.0).round(2)
    df["Última compra"] = pd.to_datetime(df["Última compra"])
    return df


@relatorio("estoque", "Posição de estoque",
           "Situação atual do estoque de todos os produtos ativos.", usa_periodo=False)
def rel_estoque(db: Session, inicio: date | None, fim: date | None) -> pd.DataFrame:
    stmt = (select(Produto.sku, Produto.nome, Produto.categoria, Produto.estoque,
                   Produto.estoque_minimo, Produto.preco_custo, Produto.preco_venda)
            .where(Produto.ativo.is_(True)).order_by(Produto.nome))
    df = _df(db, stmt, ["SKU", "Produto", "Categoria", "Estoque", "Estoque mínimo",
                        "Preço custo", "Preço venda"])
    df["Valor em estoque (custo)"] = (df["Estoque"] * df["Preço custo"]).round(2)
    df["Situação"] = np.where(df["Estoque"] <= df["Estoque mínimo"], "Baixo", "OK")
    return df


# ----------------------------------------------------------------------------
class RelatorioService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def listar() -> list[DefinicaoRelatorio]:
        return list(_REGISTRO.values())

    def gerar(self, nome: str, inicio: date | None = None,
              fim: date | None = None) -> tuple[DefinicaoRelatorio, pd.DataFrame]:
        definicao = _REGISTRO.get(nome)
        if not definicao:
            raise NotFoundError(f"Relatório '{nome}' não existe.")
        return definicao, definicao.gerador(self.db, inicio, fim)
