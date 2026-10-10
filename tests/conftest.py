"""Fixtures dos testes: API rodando sobre um banco SQLite em memória."""
import os

os.environ["DATABASE_URL"] = "sqlite://"  # precisa vir antes de importar o backend

import pytest
from fastapi.testclient import TestClient

from backend.core.database import Base, engine, init_db
from backend.main import app

API = "/api/v1"


@pytest.fixture()
def client():
    init_db()
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def produto(client):
    r = client.post(f"{API}/produtos", json={
        "sku": "P-001", "nome": "Teclado", "categoria": "Informática",
        "preco_custo": 50, "preco_venda": 100, "estoque": 10, "estoque_minimo": 2,
    })
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture()
def cliente(client):
    r = client.post(f"{API}/clientes", json={"nome": "Ana Lima", "documento": "123.456.789-09",
                                              "email": "ANA@EMAIL.COM", "uf": "sp"})
    assert r.status_code == 201, r.text
    return r.json()

