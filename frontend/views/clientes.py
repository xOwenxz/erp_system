"""Cadastro de clientes: listagem, inclusão, edição e (des)ativação."""
import pandas as pd
import streamlit as st

from frontend import api_client as api
from frontend.components import chamar, limpar_cache, tentar

st.title("👥 Clientes")

UFS = [None, "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR",
       "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]

lista, novo, editar = st.tabs(["📋 Lista", "➕ Novo", "✏️ Editar"])


def campos_cliente(c: dict | None = None) -> dict:
    c = c or {}
    l1, l2 = st.columns([2, 1])
    dados = {"nome": l1.text_input("Nome / Razão social *", value=c.get("nome", "")),
             "documento": l2.text_input("CPF / CNPJ", value=c.get("documento") or "")}
    l3, l4 = st.columns(2)
    dados["email"] = l3.text_input("E-mail", value=c.get("email") or "")
    dados["telefone"] = l4.text_input("Telefone", value=c.get("telefone") or "")
    l5, l6 = st.columns([3, 1])
    dados["cidade"] = l5.text_input("Cidade", value=c.get("cidade") or "")
    uf_atual = c.get("uf")
    dados["uf"] = l6.selectbox("UF", UFS, index=UFS.index(uf_atual) if uf_atual in UFS else 0,
                               format_func=lambda u: "-" if u is None else u)
    return {k: (v.strip() if isinstance(v, str) else v) or None for k, v in dados.items()}


# ================================================================ Lista
with lista:
    f1, f2 = st.columns([3, 1])
    busca = f1.text_input("Buscar por nome, documento ou e-mail")
    apenas_ativos = f2.toggle("Somente ativos", value=True)
    clientes = chamar(api.get, "/clientes", busca=busca or None, apenas_ativos=apenas_ativos, limit=5000)
    if not clientes:
        st.info("Nenhum cliente encontrado.")
    else:
        df = pd.DataFrame(clientes)
        df["criado_em"] = pd.to_datetime(df["criado_em"])
        st.caption(f"{len(df)} cliente(s)")
        st.dataframe(df[["nome", "documento", "email", "telefone", "cidade", "uf", "ativo", "criado_em"]],
                     hide_index=True, width="stretch", height=480, column_config={
                         "nome": "Nome", "documento": "Documento", "email": "E-mail", "telefone": "Telefone",
                         "cidade": "Cidade", "uf": "UF", "ativo": st.column_config.CheckboxColumn("Ativo"),
                         "criado_em": st.column_config.DatetimeColumn("Cadastro", format="DD/MM/YYYY")})

# ================================================================ Novo
with novo:
    with st.form("novo_cliente", clear_on_submit=True):
        dados = campos_cliente()
        if st.form_submit_button("Cadastrar", type="primary", icon="💾"):
            ok, criado = tentar(api.post, "/clientes", json=dados)
            if ok:
                limpar_cache()
                st.success(f"Cliente **{criado['nome']}** cadastrado (ID {criado['id']}).")

# ================================================================ Editar
with editar:
    todos = {c["id"]: c for c in chamar(api.get, "/clientes", apenas_ativos=False, limit=5000)}
    if not todos:
        st.info("Nenhum cliente cadastrado.")
    else:
        cid = st.selectbox("Cliente", list(todos),
                           format_func=lambda i: todos[i]["nome"] + ("" if todos[i]["ativo"] else " (inativo)"))
        c = todos[cid]
        with st.form(f"editar_cliente_{cid}"):
            dados = campos_cliente(c)
            if st.form_submit_button("Salvar alterações", type="primary", icon="💾"):
                ok, _ = tentar(api.put, f"/clientes/{cid}", json=dados)
                if ok:
                    limpar_cache()
                    st.toast("Cliente atualizado.", icon="✅")
                    st.rerun()
        if c["ativo"]:
            if st.button("Desativar cliente", icon="🚫"):
                ok, _ = tentar(api.delete, f"/clientes/{cid}")
                if ok:
                    st.toast("Cliente desativado.", icon="🚫")
                    st.rerun()
        elif st.button("Reativar cliente", icon="♻️"):
            ok, _ = tentar(api.put, f"/clientes/{cid}", json={"ativo": True})
            if ok:
                st.toast("Cliente reativado.", icon="♻️")
                st.rerun()

