"""Agregações para o dashboard (KPIs, séries temporais e rankings)."""
from datetime import date

import pandas as pd
from sqlalchemy import Float, func, select, type_coerce
from sqlalchemy.orm import Session

from backend.core.utils import filtro_periodo
from backend.models import Cliente, ItemVenda, Produto, StatusVenda, Venda
from backend.repositories import ProdutoRepository
from backend.schemas.analytics import (
    DashboardOut, ItemCategoria, ItemEstoqueBaixo, ItemRanking, KPIs, PontoSerie,
)


class DashboardService:
    def __init__(self, db: Session):
        self.db = db

    def gerar(self, inicio: date | None = None, fim: date | None = None,
              agrupamento: str = "mes", limite: int = 10) -> DashboardOut:
        filtros = [Venda.status == StatusVenda.CONCLUIDA.value,
                   *filtro_periodo(Venda.data, inicio, fim)]
        vendas = self._vendas_df(filtros)
        estoque_baixo = ProdutoRepository(self.db).estoque_baixo()

        return DashboardOut(
            periodo_inicio=inicio,
            periodo_fim=fim,
            agrupamento=agrupamento,
            kpis=self._kpis(vendas, filtros, len(estoque_baixo)),
            vendas_por_periodo=self._serie(vendas, agrupamento),
            top_produtos=self._top_produtos(filtros, limite),
            top_clientes=self._top_clientes(filtros, limite),
            vendas_por_categoria=self._por_categoria(filtros),
            estoque_baixo=[ItemEstoqueBaixo.model_validate(p, from_attributes=True)
                           for p in estoque_baixo[:limite * 2]],
        )

    # ------------------------------------------------------------------
    def _join_itens(self, *colunas):
        return (select(*colunas).select_from(ItemVenda)
                .join(Venda, ItemVenda.venda_id == Venda.id)
                .join(Produto, ItemVenda.produto_id == Produto.id))

    def _vendas_df(self, filtros) -> pd.DataFrame:
        linhas = self.db.execute(
            select(Venda.id, Venda.data, Venda.total, Venda.cliente_id).where(*filtros)
        ).all()
        df = pd.DataFrame(linhas, columns=["id", "data", "total", "cliente_id"])
        if not df.empty:
            df["data"] = pd.to_datetime(df["data"])
            df["total"] = df["total"].astype(float)
        return df

    def _kpis(self, df: pd.DataFrame, filtros, qtd_estoque_baixo: int) -> KPIs:
        faturamento = float(df["total"].sum()) if not df.empty else 0.0
        qtd_vendas = len(df)

        custo_expr = type_coerce(func.sum(ItemVenda.quantidade * Produto.preco_custo), Float)
        itens, custo = self.db.execute(
            self._join_itens(func.coalesce(func.sum(ItemVenda.quantidade), 0),
                             func.coalesce(custo_expr, 0.0)).where(*filtros)
        ).one()
        lucro = faturamento - float(custo or 0)

        valor_estoque = self.db.scalar(
            select(func.coalesce(type_coerce(func.sum(Produto.estoque * Produto.preco_custo), Float), 0.0))
            .where(Produto.ativo.is_(True))
        )

        return KPIs(
            faturamento=round(faturamento, 2),
            qtd_vendas=qtd_vendas,
            ticket_medio=round(faturamento / qtd_vendas, 2) if qtd_vendas else 0.0,
            lucro_bruto=round(lucro, 2),
            margem_bruta=round(lucro / faturamento * 100, 2) if faturamento else 0.0,
            itens_vendidos=int(itens or 0),
            clientes_ativos=int(df["cliente_id"].dropna().nunique()) if not df.empty else 0,
            valor_estoque=round(float(valor_estoque or 0), 2),
            produtos_estoque_baixo=qtd_estoque_baixo,
        )

    def _serie(self, df: pd.DataFrame, agrupamento: str) -> list[PontoSerie]:
        if df.empty:
            return []
        if agrupamento == "semana":
            grouper = pd.Grouper(key="data", freq="W-MON", label="left", closed="left")
        else:
            grouper = pd.Grouper(key="data", freq="D" if agrupamento == "dia" else "MS")
        serie = df.groupby(grouper).agg(faturamento=("total", "sum"), qtd_vendas=("id", "count"))
        return [
            PontoSerie(periodo=idx.date(), faturamento=round(float(row.faturamento), 2),
                       qtd_vendas=int(row.qtd_vendas))
            for idx, row in serie.iterrows()
        ]

    def _top_produtos(self, filtros, limite: int) -> list[ItemRanking]:
        valor = type_coerce(func.sum(ItemVenda.subtotal), Float)
        stmt = (self._join_itens(Produto.id, Produto.nome, func.sum(ItemVenda.quantidade), valor)
                .where(*filtros).group_by(Produto.id, Produto.nome)
                .order_by(valor.desc()).limit(limite))
        return [ItemRanking(id=i, nome=n, quantidade=float(q or 0), valor=round(float(v or 0), 2))
                for i, n, q, v in self.db.execute(stmt)]

    def _top_clientes(self, filtros, limite: int) -> list[ItemRanking]:
        valor = type_coerce(func.sum(Venda.total), Float)
        stmt = (select(Cliente.id, Cliente.nome, func.count(Venda.id), valor)
                .join(Cliente, Venda.cliente_id == Cliente.id)
                .where(*filtros).group_by(Cliente.id, Cliente.nome)
                .order_by(valor.desc()).limit(limite))
        return [ItemRanking(id=i, nome=n, quantidade=float(q or 0), valor=round(float(v or 0), 2))
                for i, n, q, v in self.db.execute(stmt)]

    def _por_categoria(self, filtros) -> list[ItemCategoria]:
        categoria = func.coalesce(Produto.categoria, "Sem categoria")
        valor = type_coerce(func.sum(ItemVenda.subtotal), Float)
        stmt = (self._join_itens(categoria, valor).where(*filtros)
                .group_by(categoria).order_by(valor.desc()))
        return [ItemCategoria(categoria=c, valor=round(float(v or 0), 2))
                for c, v in self.db.execute(stmt)]
