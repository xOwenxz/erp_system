"""Testes de ponta a ponta da API (cadastros, vendas, dashboard, relatórios e Excel)."""
from io import BytesIO

import pandas as pd

from tests.conftest import API


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


# ---------------------------------------------------------------- Cadastros
def test_cliente_normaliza_campos(cliente):
    assert cliente["documento"] == "12345678909"
    assert cliente["email"] == "ana@email.com"
    assert cliente["uf"] == "SP"


def test_produto_sku_duplicado(client, produto):
    r = client.post(f"{API}/produtos", json={"sku": "P-001", "nome": "Outro", "preco_venda": 1})
    assert r.status_code in (400, 409)


def test_produto_nao_encontrado(client):
    assert client.get(f"{API}/produtos/999").status_code == 404


# ---------------------------------------------------------------- Vendas
def test_venda_baixa_e_devolve_estoque(client, produto, cliente):
    r = client.post(f"{API}/vendas", json={"cliente_id": cliente["id"], "desconto": 10,
                                            "itens": [{"produto_id": produto["id"], "quantidade": 3}]})
    assert r.status_code == 201, r.text
    venda = r.json()
    assert venda["subtotal"] == 300 and venda["total"] == 290
    assert client.get(f"{API}/produtos/{produto['id']}").json()["estoque"] == 7

    r = client.post(f"{API}/vendas/{venda['id']}/cancelar")
    assert r.json()["status"] == "cancelada"
    assert client.get(f"{API}/produtos/{produto['id']}").json()["estoque"] == 10


def test_venda_estoque_insuficiente(client, produto):
    r = client.post(f"{API}/vendas", json={"itens": [{"produto_id": produto["id"], "quantidade": 99}]})
    assert r.status_code == 422  # BusinessRuleError
    assert "Estoque insuficiente" in r.json()["detail"]


# ---------------------------------------------------------------- Dashboard / relatórios
def test_dashboard(client, produto, cliente):
    client.post(f"{API}/vendas", json={"cliente_id": cliente["id"],
                                        "itens": [{"produto_id": produto["id"], "quantidade": 2}]})
    d = client.get(f"{API}/dashboard").json()
    assert d["kpis"]["faturamento"] == 200
    assert d["kpis"]["qtd_vendas"] == 1
    assert d["kpis"]["lucro_bruto"] == 100
    assert d["top_produtos"][0]["nome"] == "Teclado"


def test_relatorios_json_e_arquivos(client, produto):
    client.post(f"{API}/vendas", json={"itens": [{"produto_id": produto["id"], "quantidade": 1}]})
    nomes = [r["nome"] for r in client.get(f"{API}/relatorios").json()]
    assert {"vendas", "estoque", "clientes"} <= set(nomes)
    for nome in nomes:
        r = client.get(f"{API}/relatorios/{nome}")
        assert r.status_code == 200, (nome, r.text)
    xlsx = client.get(f"{API}/relatorios/vendas", params={"formato": "xlsx"})
    assert xlsx.content[:2] == b"PK"  # arquivos .xlsx são zip
    csv = client.get(f"{API}/relatorios/estoque", params={"formato": "csv"})
    assert "SKU" in csv.content.decode("utf-8-sig")


# ---------------------------------------------------------------- Excel
def _xlsx(df: pd.DataFrame) -> bytes:
    buf = BytesIO()
    df.to_excel(buf, index=False)
    return buf.getvalue()


def test_excel_analisar(client):
    df = pd.DataFrame({"Produto": ["A", "B", "C"], "Valor": [10.0, 20.0, 30.0]})
    r = client.post(f"{API}/excel/analisar", files={"arquivo": ("teste.xlsx", _xlsx(df))})
    assert r.status_code == 200, r.text
    dados = r.json()
    assert dados["total_linhas"] == 3
    assert dados["estatisticas"]["Valor"]["mean"] == 20.0


def test_excel_importar_produtos_com_sinonimos(client):
    df = pd.DataFrame({"Código": ["X1", "X2", None], "Descrição": ["Item 1", "Item 2", "Sem código"],
                       "Preço": ["1.234,50", 10, 5], "Qtd": [5, 3, 1]})
    r = client.post(f"{API}/excel/importar/produtos", files={"arquivo": ("p.xlsx", _xlsx(df))})
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["inseridos"] == 2
    assert len(res["erros"]) == 1 and res["erros"][0]["linha"] == 4

    # reimportar atualiza em vez de duplicar
    res = client.post(f"{API}/excel/importar/produtos", files={"arquivo": ("p.xlsx", _xlsx(df))}).json()
    assert res["atualizados"] == 2 and res["inseridos"] == 0
    precos = {p["sku"]: p["preco_venda"] for p in client.get(f"{API}/produtos").json()}
    assert precos["X1"] == 1234.5


def test_excel_modelo(client):
    r = client.get(f"{API}/excel/modelos/clientes")
    assert r.status_code == 200 and r.content[:2] == b"PK"


def test_excel_formato_invalido(client):
    r = client.post(f"{API}/excel/analisar", files={"arquivo": ("x.pdf", b"%PDF")})
    assert r.status_code == 422
    assert "Formato não suportado" in r.json()["detail"]
