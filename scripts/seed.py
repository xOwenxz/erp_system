"""Popula o banco com dados de exemplo e gera uma planilha de exemplo.

Uso:
    python -m scripts.seed            # adiciona dados (se o banco estiver vazio)
    python -m scripts.seed --reset    # apaga tudo e recria
"""
import argparse
import random
from datetime import datetime, time, timedelta
from pathlib import Path

import pandas as pd
from sqlalchemy import func, select

from backend.core.config import BASE_DIR
from backend.core.database import Base, SessionLocal, engine, init_db
from backend.models import Produto
from backend.schemas.cliente import ClienteCreate
from backend.schemas.produto import ProdutoCreate
from backend.schemas.venda import ItemVendaIn, VendaCreate
from backend.services.cliente_service import ClienteService
from backend.services.produto_service import ProdutoService
from backend.services.venda_service import VendaService

random.seed(42)

PRODUTOS = [  # (sku, nome, categoria, custo, venda)
    ("INF-001", "Notebook 15\"", "Informática", 2800, 3999.9),
    ("INF-002", "Mouse sem fio", "Informática", 35, 79.9),
    ("INF-003", "Teclado mecânico", "Informática", 180, 349.9),
    ("INF-004", "Monitor 24\"", "Informática", 650, 999.9),
    ("INF-005", "Webcam Full HD", "Informática", 120, 229.9),
    ("INF-006", "SSD 1TB", "Informática", 320, 549.9),
    ("MOV-001", "Cadeira de escritório", "Móveis", 250, 499.9),
    ("MOV-002", "Mesa em L", "Móveis", 480, 899.9),
    ("MOV-003", "Gaveteiro", "Móveis", 160, 319.9),
    ("MOV-004", "Estante 5 prateleiras", "Móveis", 210, 389.9),
    ("PAP-001", "Resma papel A4", "Papelaria", 18, 32.9),
    ("PAP-002", "Caneta esferográfica (cx 50)", "Papelaria", 25, 49.9),
    ("PAP-003", "Caderno universitário", "Papelaria", 9, 22.9),
    ("PAP-004", "Grampeador", "Papelaria", 14, 34.9),
    ("ELE-001", "Fone Bluetooth", "Eletrônicos", 90, 199.9),
    ("ELE-002", "Caixa de som portátil", "Eletrônicos", 110, 239.9),
    ("ELE-003", "Carregador USB-C 65W", "Eletrônicos", 60, 139.9),
    ("ELE-004", "Smartwatch", "Eletrônicos", 380, 749.9),
    ("LIM-001", "Detergente 5L", "Limpeza", 12, 27.9),
    ("LIM-002", "Papel toalha (fardo)", "Limpeza", 30, 59.9),
]

NOMES = ["Ana", "Bruno", "Carla", "Diego", "Eduarda", "Felipe", "Gabriela", "Henrique", "Isabela", "João",
         "Larissa", "Marcos", "Natália", "Otávio", "Patrícia", "Rafael", "Sabrina", "Thiago", "Vanessa", "William"]
SOBRENOMES = ["Silva", "Souza", "Oliveira", "Santos", "Lima", "Pereira", "Costa", "Almeida", "Ribeiro", "Gomes"]
EMPRESAS = ["Tech Soluções LTDA", "Escritório Central ME", "Grupo Horizonte SA", "Papelaria Ponto Certo",
            "Construtora Alicerce", "Clínica Bem Estar", "Escola Saber Mais", "Agência Criativa"]
CIDADES = [("São Paulo", "SP"), ("Rio de Janeiro", "RJ"), ("Belo Horizonte", "MG"), ("Curitiba", "PR"),
           ("Porto Alegre", "RS"), ("Salvador", "BA"), ("Recife", "PE"), ("Goiânia", "GO"), ("Campinas", "SP")]


def _resetar():
    import backend.models  # noqa: F401

    Base.metadata.drop_all(bind=engine)
    init_db()


def _popular(qtd_vendas: int, dias: int):
    db = SessionLocal()
    try:
        if db.scalar(select(func.count(Produto.id))):
            print("O banco já possui dados. Use --reset para recriar.")
            return

        produtos = [ProdutoService(db).criar(ProdutoCreate(
            sku=sku, nome=nome, categoria=cat, preco_custo=custo, preco_venda=venda,
            estoque=random.randint(150, 600), estoque_minimo=random.choice([5, 10, 20, 30])))
            for sku, nome, cat, custo, venda in PRODUTOS]

        clientes = []
        for i in range(30):
            cidade, uf = random.choice(CIDADES)
            if i < len(EMPRESAS):
                nome, doc = EMPRESAS[i], f"{random.randint(10, 99)}{random.randint(10**10, 10**11 - 1)}"[:14]
            else:
                nome = f"{random.choice(NOMES)} {random.choice(SOBRENOMES)} {random.choice(SOBRENOMES)}"
                doc = str(random.randint(10**10, 10**11 - 1))
            email = nome.lower().split()[0] + f"{i}@exemplo.com.br"
            clientes.append(ClienteService(db).criar(ClienteCreate(
                nome=nome, documento=doc, email=email, telefone=f"(11) 9{random.randint(1000, 9999)}-{i:04d}",
                cidade=cidade, uf=uf)))

        # Vendas ao longo do período, com leve tendência de crescimento e sazonalidade semanal
        inicio = datetime.now() - timedelta(days=dias)
        pesos_produtos = [random.uniform(0.3, 3) for _ in produtos]
        vendas_svc = VendaService(db)
        criadas = 0
        for _ in range(qtd_vendas):
            dia = inicio + timedelta(days=int(dias * random.random() ** 0.8))
            if dia.weekday() == 6 and random.random() < 0.7:
                continue  # domingo com menos movimento
            data = datetime.combine(dia.date(), time(random.randint(8, 19), random.randint(0, 59)))
            escolhidos = random.choices(produtos, weights=pesos_produtos, k=random.randint(1, 4))
            itens = [ItemVendaIn(produto_id=p.id, quantidade=random.randint(1, 5)) for p in escolhidos]
            cliente = random.choice(clientes) if random.random() < 0.85 else None
            try:
                venda = vendas_svc.criar(VendaCreate(cliente_id=cliente.id if cliente else None, data=data,
                                                     desconto=random.choice([0, 0, 0, 5, 10]), itens=itens))
                criadas += 1
                if random.random() < 0.03:
                    vendas_svc.cancelar(venda.id)
            except Exception:  # noqa: BLE001 - ex.: estoque esgotado; apenas ignora a venda
                continue

        # Alguns produtos com estoque baixo para o alerta do dashboard
        for p in random.sample(produtos, 3):
            p.estoque = random.randint(0, p.estoque_minimo)
        db.commit()
        print(f"OK: {len(produtos)} produtos, {len(clientes)} clientes, {criadas} vendas.")
    finally:
        db.close()


def _planilha_exemplo():
    """Planilha com 'cara de planilha real' para testar a leitura/análise de Excel."""
    destino = BASE_DIR / "data" / "exemplos"
    destino.mkdir(parents=True, exist_ok=True)
    meses = pd.date_range(end=pd.Timestamp.today().normalize(), periods=12, freq="MS")
    linhas = [{"Mês": m.date(), "Região": r, "Vendedor": v, "Meta (R$)": meta,
               "Realizado (R$)": round(meta * random.uniform(0.7, 1.3), 2)}
              for m in meses
              for r, v, meta in [("Sudeste", "Carlos", 50000), ("Sul", "Fernanda", 35000),
                                 ("Nordeste", "Juliana", 28000), ("Centro-Oeste", "Roberto", 20000)]]
    vendas = pd.DataFrame(linhas)
    vendas["% Meta"] = (vendas["Realizado (R$)"] / vendas["Meta (R$)"] * 100).round(1)
    novos_produtos = pd.DataFrame([
        {"Código": "NOV-001", "Descrição": "Hub USB 7 portas", "Grupo": "Informática", "Custo": "45,00",
         "Preço": "99,90", "Qtd": 40},
        {"Código": "NOV-002", "Descrição": "Suporte para notebook", "Grupo": "Informática", "Custo": "38,50",
         "Preço": "89,90", "Qtd": 25},
        {"Código": "NOV-003", "Descrição": "Luminária LED de mesa", "Grupo": "Móveis", "Custo": "52,00",
         "Preço": "119,90", "Qtd": 15},
    ])
    caminho = destino / "planilha_exemplo.xlsx"
    with pd.ExcelWriter(caminho) as w:
        vendas.to_excel(w, sheet_name="Vendas por região", index=False)
        novos_produtos.to_excel(w, sheet_name="Novos produtos", index=False)
    print(f"Planilha de exemplo: {caminho}")


def main():
    parser = argparse.ArgumentParser(description="Gera dados de exemplo para o ERP.")
    parser.add_argument("--reset", action="store_true", help="apaga e recria todas as tabelas")
    parser.add_argument("--vendas", type=int, default=600, help="quantidade aproximada de vendas")
    parser.add_argument("--dias", type=int, default=365, help="período (dias para trás)")
    args = parser.parse_args()

    if args.reset:
        _resetar()
    else:
        init_db()
    _popular(args.vendas, args.dias)
    _planilha_exemplo()


if __name__ == "__main__":
    main()

