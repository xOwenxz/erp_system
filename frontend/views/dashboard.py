"""Dashboard: KPIs, evolução de vendas, rankings e alertas de estoque."""
import pandas as pd
import plotly.express as px
import streamlit as st

from frontend import api_client as api
from frontend.components import brl, chamar, filtro_periodo, numero

st.title("📊 Dashboard")


@st.cache_data(ttl=30, show_spinner="Carregando indicadores...")
def carregar(inicio, fim, agrupamento, limite):
    return api.get("/dashboard", inicio=inicio, fim=fim, agrupamento=agrupamento, limite=limite)


c1, c2 = st.columns([3, 1])
with c1:
    inicio, fim = filtro_periodo("dash")
agrupamento = c2.segmented_control("Agrupar por", ["dia", "semana", "mes"], default="mes",
                                   format_func={"dia": "Dia", "semana": "Semana", "mes": "Mês"}.get) or "mes"

d = chamar(carregar, inicio, fim, agrupamento, 10)
k = d["kpis"]

# ---------------------------------------------------------------- KPIs
linha1 = st.columns(4)
linha1[0].metric("Faturamento", brl(k["faturamento"]), border=True)
linha1[1].metric("Vendas", numero(k["qtd_vendas"]), border=True)
linha1[2].metric("Ticket médio", brl(k["ticket_medio"]), border=True)
linha1[3].metric("Lucro bruto", brl(k["lucro_bruto"]), f"{numero(k['margem_bruta'], 1)}% de margem",
                 delta_color="off", border=True)
linha2 = st.columns(4)
linha2[0].metric("Itens vendidos", numero(k["itens_vendidos"]), border=True)
linha2[1].metric("Clientes ativos no período", numero(k["clientes_ativos"]), border=True)
linha2[2].metric("Valor em estoque (custo)", brl(k["valor_estoque"]), border=True)
linha2[3].metric("Produtos com estoque baixo", numero(k["produtos_estoque_baixo"]), border=True,
                 delta="Atenção" if k["produtos_estoque_baixo"] else None, delta_color="inverse")

if not d["vendas_por_periodo"]:
    st.info("Nenhuma venda no período selecionado. Cadastre vendas ou rode `python -m scripts.seed` "
            "para gerar dados de exemplo.")
    st.stop()

# ---------------------------------------------------------------- Gráficos
serie = pd.DataFrame(d["vendas_por_periodo"])
serie["periodo"] = pd.to_datetime(serie["periodo"])
fig = px.bar(serie, x="periodo", y="faturamento", labels={"periodo": "", "faturamento": "Faturamento (R$)"},
             hover_data={"qtd_vendas": True}, color_discrete_sequence=["#1F4E78"])
fig.add_scatter(x=serie["periodo"], y=serie["faturamento"].rolling(3, min_periods=1).mean(),
                mode="lines", name="Média móvel (3)", line={"color": "#F39C12"})
fig.update_layout(title="Faturamento por período", height=380, margin={"t": 50, "b": 10}, legend={"orientation": "h"})
st.plotly_chart(fig, width="stretch")

g1, g2 = st.columns(2)
with g1:
    cat = pd.DataFrame(d["vendas_por_categoria"])
    if not cat.empty:
        fig = px.pie(cat, names="categoria", values="valor", hole=0.5, title="Faturamento por categoria")
        fig.update_layout(height=380, margin={"t": 50, "b": 10})
        st.plotly_chart(fig, width="stretch")
with g2:
    prod = pd.DataFrame(d["top_produtos"])
    if not prod.empty:
        fig = px.bar(prod.sort_values("valor"), x="valor", y="nome", orientation="h", title="Top produtos",
                     labels={"valor": "Faturamento (R$)", "nome": ""}, hover_data={"quantidade": True},
                     color_discrete_sequence=["#2E86C1"])
        fig.update_layout(height=380, margin={"t": 50, "b": 10})
        st.plotly_chart(fig, width="stretch")

t1, t2 = st.columns(2)
with t1:
    st.subheader("🏆 Top clientes")
    cli = pd.DataFrame(d["top_clientes"])
    if not cli.empty:
        st.dataframe(cli[["nome", "quantidade", "valor"]], hide_index=True, width="stretch", column_config={
            "nome": "Cliente",
            "quantidade": st.column_config.NumberColumn("Compras", format="%d"),
            "valor": st.column_config.ProgressColumn("Total (R$)", format="R$ %.2f",
                                                     min_value=0, max_value=float(cli["valor"].max())),
        })
with t2:
    st.subheader("⚠️ Estoque baixo")
    baixo = pd.DataFrame(d["estoque_baixo"])
    if baixo.empty:
        st.success("Nenhum produto abaixo do estoque mínimo.")
    else:
        st.dataframe(baixo[["sku", "nome", "estoque", "estoque_minimo"]], hide_index=True, width="stretch",
                     column_config={"sku": "SKU", "nome": "Produto", "estoque": "Estoque",
                                    "estoque_minimo": "Mínimo"})

