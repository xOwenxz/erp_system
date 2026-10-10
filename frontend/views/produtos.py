"""Cadastro de produtos: listagem, inclusão, edição e (des)ativação."""
import pandas as pd
import streamlit as st

from frontend import api_client as api
from frontend.components import chamar, limpar_cache, tentar

st.title("📦 Produtos")

lista, novo, editar = st.tabs(["📋 Lista", "➕ Novo", "✏️ Editar"])


def campos_produto(p: dict | None = None) -> dict:
    p = p or {}
    c1, c2, c3 = st.columns([1, 2, 1])
    dados = {
        "sku": c1.text_input("SKU *", value=p.get("sku", "")),
        "nome": c2.text_input("Nome *", value=p.get("nome", "")),
        "categoria": c3.text_input("Categoria", value=p.get("categoria") or ""),
    }
    c4, c5, c6, c7 = st.columns(4)
    dados["preco_custo"] = c4.number_input("Preço de custo", min_value=0.0, step=0.01, format="%.2f",
                                           value=float(p.get("preco_custo", 0)))
    dados["preco_venda"] = c5.number_input("Preço de venda *", min_value=0.0, step=0.01, format="%.2f",
                                           value=float(p.get("preco_venda", 0)))
    dados["estoque"] = c6.number_input("Estoque", min_value=0, step=1, value=int(p.get("estoque", 0)))
    dados["estoque_minimo"] = c7.number_input("Estoque mínimo", min_value=0, step=1,
                                              value=int(p.get("estoque_minimo", 0)))
    dados["categoria"] = dados["categoria"] or None
    return dados


# ================================================================ Lista
with lista:
    f1, f2, f3 = st.columns([2, 1, 1])
    busca = f1.text_input("Buscar por nome ou SKU")
    categoria = f2.selectbox("Categoria", [None, *chamar(api.get, "/produtos/categorias")],
                             format_func=lambda c: "Todas" if c is None else c)
    apenas_ativos = f3.toggle("Somente ativos", value=True)
    produtos = chamar(api.get, "/produtos", busca=busca or None, categoria=categoria,
                      apenas_ativos=apenas_ativos, limit=5000)
    if not produtos:
        st.info("Nenhum produto encontrado. Cadastre na aba **Novo** ou importe uma planilha em **Planilhas Excel**.")
    else:
        df = pd.DataFrame(produtos)
        st.caption(f"{len(df)} produto(s)")
        st.dataframe(df[["sku", "nome", "categoria", "preco_custo", "preco_venda", "estoque", "estoque_minimo",
                         "estoque_baixo", "ativo"]], hide_index=True, width="stretch", height=480, column_config={
            "sku": "SKU", "nome": "Nome", "categoria": "Categoria",
            "preco_custo": st.column_config.NumberColumn("Custo", format="R$ %.2f"),
            "preco_venda": st.column_config.NumberColumn("Venda", format="R$ %.2f"),
            "estoque": "Estoque", "estoque_minimo": "Mínimo",
            "estoque_baixo": st.column_config.CheckboxColumn("Baixo?"),
            "ativo": st.column_config.CheckboxColumn("Ativo"),
        })

# ================================================================ Novo
with novo:
    with st.form("novo_produto", clear_on_submit=True):
        dados = campos_produto()
        if st.form_submit_button("Cadastrar", type="primary", icon="💾"):
            ok, criado = tentar(api.post, "/produtos", json=dados)
            if ok:
                limpar_cache()
                st.success(f"Produto **{criado['nome']}** cadastrado (ID {criado['id']}).")

# ================================================================ Editar
with editar:
    todos = {p["id"]: p for p in chamar(api.get, "/produtos", apenas_ativos=False, limit=5000)}
    if not todos:
        st.info("Nenhum produto cadastrado.")
    else:
        pid = st.selectbox("Produto", list(todos), format_func=lambda i: f"{todos[i]['sku']} · {todos[i]['nome']}"
                           + ("" if todos[i]["ativo"] else " (inativo)"))
        p = todos[pid]
        with st.form(f"editar_produto_{pid}"):
            dados = campos_produto(p)
            if st.form_submit_button("Salvar alterações", type="primary", icon="💾"):
                ok, _ = tentar(api.put, f"/produtos/{pid}", json=dados)
                if ok:
                    limpar_cache()
                    st.toast("Produto atualizado.", icon="✅")
                    st.rerun()
        if p["ativo"]:
            if st.button("Desativar produto", icon="🚫"):
                ok, _ = tentar(api.delete, f"/produtos/{pid}")
                if ok:
                    st.toast("Produto desativado.", icon="🚫")
                    st.rerun()
        elif st.button("Reativar produto", icon="♻️"):
            ok, _ = tentar(api.put, f"/produtos/{pid}", json={"ativo": True})
            if ok:
                st.toast("Produto reativado.", icon="♻️")
                st.rerun()

