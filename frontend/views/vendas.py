"""Vendas: registro de novas vendas (carrinho) e histórico com cancelamento."""
import pandas as pd
import streamlit as st

from frontend import api_client as api
from frontend.components import brl, chamar, filtro_periodo, limpar_cache, tentar

st.title("🛒 Vendas")

if "carrinho" not in st.session_state:
    st.session_state.carrinho = []  # [{produto_id, quantidade, preco_unitario}]

nova, historico = st.tabs(["➕ Nova venda", "📜 Histórico"])

# ================================================================ Nova venda
with nova:
    produtos = {p["id"]: p for p in chamar(api.get, "/produtos", limit=5000)}
    clientes = {c["id"]: c for c in chamar(api.get, "/clientes", limit=5000)}
    if not produtos:
        st.info("Cadastre produtos antes de registrar vendas.")
        st.stop()

    with st.form("add_item", clear_on_submit=True, border=True):
        c1, c2, c3, c4 = st.columns([4, 1, 1.4, 1])
        produto_id = c1.selectbox(
            "Produto", list(produtos),
            format_func=lambda i: f"{produtos[i]['sku']} · {produtos[i]['nome']} "
                                  f"(estoque {produtos[i]['estoque']} · {brl(produtos[i]['preco_venda'])})")
        quantidade = c2.number_input("Qtd.", min_value=1, value=1, step=1)
        preco = c3.number_input("Preço unit. (vazio = tabela)", min_value=0.0, value=None, step=0.01, format="%.2f")
        c4.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if c4.form_submit_button("Adicionar", icon="➕", width="stretch"):
            st.session_state.carrinho.append({"produto_id": produto_id, "quantidade": int(quantidade),
                                              "preco_unitario": preco})

    carrinho = st.session_state.carrinho
    if not carrinho:
        st.caption("O carrinho está vazio. Adicione produtos acima.")
    else:
        linhas = []
        for item in carrinho:
            p = produtos.get(item["produto_id"], {})
            preco_item = item["preco_unitario"] if item["preco_unitario"] is not None else p.get("preco_venda", 0)
            linhas.append({"SKU": p.get("sku"), "Produto": p.get("nome"), "Qtd.": item["quantidade"],
                           "Preço unit.": preco_item, "Subtotal": round(preco_item * item["quantidade"], 2)})
        tabela = pd.DataFrame(linhas)
        tabela.insert(0, "Remover", False)
        editado = st.data_editor(tabela, hide_index=True, width="stretch", disabled=list(tabela.columns[1:]),
                                 column_config={"Preço unit.": st.column_config.NumberColumn(format="R$ %.2f"),
                                                "Subtotal": st.column_config.NumberColumn(format="R$ %.2f")},
                                 key=f"carrinho_{len(carrinho)}")
        if editado["Remover"].any():
            st.session_state.carrinho = [i for i, rem in zip(carrinho, editado["Remover"]) if not rem]
            st.rerun()

        subtotal = float(tabela["Subtotal"].sum())
        f1, f2 = st.columns(2)
        cliente_id = f1.selectbox("Cliente", [None, *clientes],
                                  format_func=lambda i: "Consumidor final" if i is None else clientes[i]["nome"])
        desconto = f2.number_input("Desconto (R$)", min_value=0.0, max_value=subtotal, value=0.0, step=1.0)
        observacao = st.text_input("Observação", max_chars=500)

        r1, r2, r3 = st.columns([2, 1, 1])
        r1.markdown(f"### Total: {brl(subtotal - desconto)}")
        if r2.button("Limpar carrinho", icon="🗑️", width="stretch"):
            st.session_state.carrinho = []
            st.rerun()
        if r3.button("Finalizar venda", type="primary", icon="✅", width="stretch"):
            ok, venda = tentar(api.post, "/vendas", json={
                "cliente_id": cliente_id, "desconto": desconto, "observacao": observacao or None,
                "itens": carrinho})
            if ok:
                st.session_state.carrinho = []
                limpar_cache()
                st.toast(f"Venda #{venda['id']} registrada: {brl(venda['total'])}", icon="✅")
                st.rerun()

# ================================================================ Histórico
with historico:
    h1, h2 = st.columns([3, 1])
    with h1:
        inicio, fim = filtro_periodo("vendas_hist", padrao="Últimos 30 dias")
    status = h2.selectbox("Status", [None, "concluida", "cancelada"],
                          format_func=lambda s: "Todos" if s is None else s.capitalize())
    vendas = chamar(api.get, "/vendas", inicio=inicio, fim=fim, status=status, limit=5000)
    if not vendas:
        st.info("Nenhuma venda encontrada.")
        st.stop()

    df = pd.DataFrame(vendas)
    df["data"] = pd.to_datetime(df["data"])
    df["cliente_nome"] = df["cliente_nome"].fillna("Consumidor final")
    df["itens_qtd"] = df["itens"].apply(lambda itens: sum(i["quantidade"] for i in itens))
    st.caption(f"{len(df)} venda(s) · total concluído: "
               f"{brl(df.loc[df['status'] == 'concluida', 'total'].sum())} · clique em uma linha para detalhes")

    sel = st.dataframe(
        df[["id", "data", "cliente_nome", "status", "itens_qtd", "subtotal", "desconto", "total"]],
        hide_index=True, width="stretch", height=380, on_select="rerun", selection_mode="single-row",
        column_config={
            "id": "Nº", "data": st.column_config.DatetimeColumn("Data", format="DD/MM/YYYY HH:mm"),
            "cliente_nome": "Cliente", "status": "Status", "itens_qtd": "Itens",
            "subtotal": st.column_config.NumberColumn("Subtotal", format="R$ %.2f"),
            "desconto": st.column_config.NumberColumn("Desconto", format="R$ %.2f"),
            "total": st.column_config.NumberColumn("Total", format="R$ %.2f"),
        })

    if sel.selection.rows:
        venda = vendas[sel.selection.rows[0]]
        with st.container(border=True):
            st.markdown(f"**Venda #{venda['id']}** · {venda['cliente_nome'] or 'Consumidor final'} · "
                        f"status **{venda['status']}**")
            if venda["observacao"]:
                st.caption(venda["observacao"])
            st.dataframe(pd.DataFrame(venda["itens"])[["produto_sku", "produto_nome", "quantidade",
                                                       "preco_unitario", "subtotal"]],
                         hide_index=True, width="stretch", column_config={
                             "produto_sku": "SKU", "produto_nome": "Produto", "quantidade": "Qtd.",
                             "preco_unitario": st.column_config.NumberColumn("Preço unit.", format="R$ %.2f"),
                             "subtotal": st.column_config.NumberColumn("Subtotal", format="R$ %.2f")})
            if venda["status"] == "concluida" and st.button("Cancelar venda (devolve itens ao estoque)",
                                                            icon="↩️"):
                ok, _ = tentar(api.post, f"/vendas/{venda['id']}/cancelar")
                if ok:
                    limpar_cache()
                    st.toast(f"Venda #{venda['id']} cancelada.", icon="↩️")
                    st.rerun()

