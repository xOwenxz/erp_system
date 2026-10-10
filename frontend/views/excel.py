"""Planilhas Excel/CSV: leitura, análise exploratória e importação para o sistema."""
import pandas as pd
import plotly.express as px
import streamlit as st

from frontend import api_client as api
from frontend.components import chamar, limpar_cache, tentar

st.title("📗 Planilhas Excel")

arquivo = st.file_uploader("Envie uma planilha", type=["xlsx", "xlsm", "csv"],
                           help="Formatos aceitos: .xlsx, .xlsm e .csv (separador detectado automaticamente).")
if not arquivo:
    st.info("Envie um arquivo para analisar os dados ou importá-los como produtos/clientes.")
    st.stop()

conteudo = arquivo.getvalue()
aba_analisar, aba_importar = st.tabs(["🔍 Analisar dados", "⬆️ Importar para o sistema"])


@st.cache_data(show_spinner="Lendo planilha...", max_entries=5)
def analisar(nome: str, dados: bytes, aba: str | None):
    return api.post("/excel/analisar", files={"arquivo": (nome, dados)}, aba=aba)


# ================================================================ Análise
with aba_analisar:
    primeira = chamar(analisar, arquivo.name, conteudo, None)
    aba = primeira["aba"]
    if len(primeira["abas"]) > 1:
        aba = st.selectbox("Aba da planilha", primeira["abas"])
    resultado = primeira if aba == primeira["aba"] else chamar(analisar, arquivo.name, conteudo, aba)

    df = pd.DataFrame(resultado["dados"])
    m = st.columns(4)
    m[0].metric("Linhas", resultado["total_linhas"], border=True)
    m[1].metric("Colunas", resultado["total_colunas"], border=True)
    m[2].metric("Abas", len(resultado["abas"]), border=True)
    m[3].metric("Células vazias", sum(c["nulos"] for c in resultado["colunas"]), border=True)
    if resultado["truncado"]:
        st.warning(f"Exibindo as primeiras {len(df)} linhas de {resultado['total_linhas']}.")

    st.subheader("Dados")
    busca = st.text_input("Filtrar linhas (contém)", placeholder="Digite para filtrar em todas as colunas")
    visivel = df
    if busca:
        mascara = df.astype(str).apply(lambda s: s.str.contains(busca, case=False, regex=False)).any(axis=1)
        visivel = df[mascara]
    st.dataframe(visivel, width="stretch", height=350)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Perfil das colunas")
        st.dataframe(pd.DataFrame(resultado["colunas"]), hide_index=True, width="stretch", column_config={
            "nome": "Coluna", "tipo": "Tipo", "nao_nulos": "Preenchidas", "nulos": "Vazias",
            "unicos": "Valores únicos", "exemplo": "Exemplo"})
    with c2:
        st.subheader("Estatísticas")
        if resultado["estatisticas"]:
            est = pd.DataFrame(resultado["estatisticas"]).rename(index={
                "count": "Contagem", "mean": "Média", "std": "Desvio padrão", "min": "Mínimo",
                "25%": "1º quartil", "50%": "Mediana", "75%": "3º quartil", "max": "Máximo"})
            st.dataframe(est, width="stretch")
        else:
            st.caption("Nenhuma coluna numérica encontrada.")

    # ------------------------------------------------------------ Gráficos
    numericas = df.select_dtypes("number").columns.tolist()
    if not df.empty:
        st.subheader("📈 Visualização")
        g = st.columns(4)
        tipo = g[0].selectbox("Tipo de gráfico", ["Barras", "Linha", "Pizza", "Dispersão", "Histograma"])
        x = g[1].selectbox("Eixo X / Categoria", df.columns.tolist())
        if tipo == "Histograma":
            fig = px.histogram(df, x=x)
        elif not numericas:
            fig = None
            st.caption("É necessária ao menos uma coluna numérica para este gráfico.")
        else:
            y = g[2].selectbox("Valor (Y)", numericas)
            if tipo == "Dispersão":
                fig = px.scatter(df, x=x, y=y)
            else:
                agg = g[3].selectbox("Cálculo", ["sum", "mean", "count"],
                                     format_func={"sum": "Soma", "mean": "Média", "count": "Contagem"}.get)
                res = df.groupby(x, dropna=False)[y].agg(agg).reset_index()
                if tipo == "Barras":
                    fig = px.bar(res.sort_values(y, ascending=False).head(50), x=x, y=y)
                elif tipo == "Linha":
                    fig = px.line(res.sort_values(x), x=x, y=y, markers=True)
                else:
                    fig = px.pie(res, names=x, values=y, hole=0.4)
        if fig is not None:
            st.plotly_chart(fig, width="stretch")

# ================================================================ Importação
with aba_importar:
    entidades = {e["entidade"]: e for e in chamar(api.get, "/excel/entidades")}
    entidade = st.radio("Importar como", list(entidades), horizontal=True, format_func=str.capitalize)
    campos = pd.DataFrame(entidades[entidade]["campos"])
    campos["aliases"] = campos["aliases"].apply(", ".join)

    st.markdown("A primeira linha da planilha deve conter os nomes das colunas. "
                "Sinônimos comuns são reconhecidos automaticamente (ex.: *Código* → `sku`, *Preço* → `preco_venda`). "
                "Registros existentes (mesmo SKU / documento / e-mail) são **atualizados**.")
    st.dataframe(campos, hide_index=True, width="stretch", column_config={
        "nome": "Campo", "tipo": "Tipo", "obrigatorio": st.column_config.CheckboxColumn("Obrigatório"),
        "aliases": "Também aceita"})
    st.download_button(f"Baixar modelo de {entidade}", icon="📥",
                       data=chamar(api.get_bytes, f"/excel/modelos/{entidade}"),
                       file_name=f"modelo_{entidade}.xlsx")

    aba_imp = None
    if len(primeira["abas"]) > 1:
        aba_imp = st.selectbox("Aba a importar", primeira["abas"], key="aba_imp")

    if st.button(f"Importar {arquivo.name}", type="primary", icon="⬆️"):
        with st.spinner("Importando..."):
            ok, res = tentar(api.post, f"/excel/importar/{entidade}",
                             files={"arquivo": (arquivo.name, conteudo)}, aba=aba_imp)
        if ok:
            limpar_cache()
            r = st.columns(4)
            r[0].metric("Linhas lidas", res["total_linhas"])
            r[1].metric("Inseridos", res["inseridos"])
            r[2].metric("Atualizados", res["atualizados"])
            r[3].metric("Com erro", len(res["erros"]))
            if res["erros"]:
                st.warning("Algumas linhas não foram importadas:")
                st.dataframe(pd.DataFrame(res["erros"]), hide_index=True, width="stretch",
                             column_config={"linha": "Linha na planilha", "erro": "Motivo"})
            else:
                st.success("Importação concluída sem erros!")

