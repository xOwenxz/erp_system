"""Relatórios: gera qualquer relatório registrado no backend, analisa e exporta (Excel/CSV)."""
import pandas as pd
import plotly.express as px
import streamlit as st

from frontend import api_client as api
from frontend.components import chamar, filtro_periodo

st.title("📑 Relatórios")

relatorios = chamar(api.get, "/relatorios")
if not relatorios:
    st.info("Nenhum relatório disponível.")
    st.stop()

por_nome = {r["nome"]: r for r in relatorios}
nome = st.selectbox("Relatório", list(por_nome), format_func=lambda n: por_nome[n]["titulo"])
info = por_nome[nome]
st.caption(info["descricao"])

inicio = fim = None
if info["usa_periodo"]:
    inicio, fim = filtro_periodo("rel", padrao="Este ano")

params = {"inicio": inicio, "fim": fim}
chave = (nome, str(inicio), str(fim))

if st.button("Gerar relatório", type="primary", icon="▶️") or st.session_state.get("rel_chave") == chave:
    if st.session_state.get("rel_chave") != chave:
        with st.spinner("Gerando..."):
            st.session_state.rel_dados = chamar(api.get, f"/relatorios/{nome}", **params)
            st.session_state.rel_chave = chave
    dados = st.session_state.rel_dados
    df = pd.DataFrame(dados["linhas"], columns=dados["colunas"])

    topo = st.columns([2, 1, 1])
    topo[0].markdown(f"**{dados['titulo']}** · {dados['total_linhas']} linha(s)")
    with topo[1]:
        st.download_button("Baixar Excel", icon="📗", width="stretch",
                           data=chamar(api.get_bytes, f"/relatorios/{nome}", formato="xlsx", **params),
                           file_name=f"relatorio_{nome}.xlsx")
    with topo[2]:
        st.download_button("Baixar CSV", icon="📄", width="stretch",
                           data=chamar(api.get_bytes, f"/relatorios/{nome}", formato="csv", **params),
                           file_name=f"relatorio_{nome}.csv")

    if df.empty:
        st.info("O relatório não retornou dados para o período.")
        st.stop()

    for col in df.columns:  # datas ISO -> datetime para ordenar/filtrar corretamente
        if df[col].dtype == object and df[col].astype(str).str.match(r"^\d{4}-\d{2}-\d{2}T").all():
            df[col] = pd.to_datetime(df[col])

    st.dataframe(df, hide_index=True, width="stretch", height=420)

    # ------------------------------------------------------------ Análise rápida
    numericas = df.select_dtypes("number").columns.tolist()
    categoricas = [c for c in df.columns if c not in numericas]
    if numericas and categoricas:
        with st.expander("📈 Análise rápida (agrupar e visualizar)", expanded=False):
            a1, a2, a3, a4 = st.columns(4)
            grupo = a1.selectbox("Agrupar por", categoricas, key="rel_grupo")
            valor = a2.selectbox("Valor", numericas, key="rel_valor")
            agg = a3.selectbox("Cálculo", ["sum", "mean", "count", "max", "min"], key="rel_agg",
                               format_func={"sum": "Soma", "mean": "Média", "count": "Contagem",
                                            "max": "Máximo", "min": "Mínimo"}.get)
            tipo = a4.selectbox("Gráfico", ["Barras", "Linha", "Pizza"], key="rel_tipo")
            base = df.copy()
            if pd.api.types.is_datetime64_any_dtype(base[grupo]):
                base[grupo] = base[grupo].dt.to_period("M").dt.to_timestamp()
            res = base.groupby(grupo, dropna=False)[valor].agg(agg).reset_index().round(2)
            if tipo == "Barras":
                fig = px.bar(res.sort_values(valor, ascending=False).head(30), x=grupo, y=valor)
            elif tipo == "Linha":
                fig = px.line(res.sort_values(grupo), x=grupo, y=valor, markers=True)
            else:
                fig = px.pie(res, names=grupo, values=valor, hole=0.4)
            st.plotly_chart(fig, width="stretch")
            st.dataframe(res, hide_index=True, width="stretch")

