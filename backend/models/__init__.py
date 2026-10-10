"""Importar todos os modelos aqui garante que fiquem registrados no metadata."""
from backend.models.cliente import Cliente
from backend.models.produto import Produto
from backend.models.venda import ItemVenda, StatusVenda, Venda

__all__ = ["Cliente", "Produto", "Venda", "ItemVenda", "StatusVenda"]
