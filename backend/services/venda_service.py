from datetime import datetime

from sqlalchemy.orm import Session

from backend.core.exceptions import BusinessRuleError, NotFoundError
from backend.models import Cliente, ItemVenda, Produto, StatusVenda, Venda
from backend.repositories import VendaRepository
from backend.schemas.venda import VendaCreate


class VendaService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = VendaRepository(db)

    def listar(self, **filtros) -> list[Venda]:
        return self.repo.buscar(**filtros)

    def obter(self, venda_id: int) -> Venda:
        venda = self.repo.get_completa(venda_id)
        if not venda:
            raise NotFoundError(f"Venda {venda_id} não encontrada.")
        return venda

    def criar(self, dados: VendaCreate) -> Venda:
        """Registra a venda, valida e baixa o estoque em uma única transação."""
        try:
            if dados.cliente_id is not None:
                cliente = self.db.get(Cliente, dados.cliente_id)
                if not cliente:
                    raise NotFoundError(f"Cliente {dados.cliente_id} não encontrado.")
                if not cliente.ativo:
                    raise BusinessRuleError(f"Cliente '{cliente.nome}' está inativo.")

            # Consolida itens repetidos do mesmo produto
            itens: dict[int, dict] = {}
            for item in dados.itens:
                atual = itens.setdefault(item.produto_id, {"quantidade": 0, "preco": item.preco_unitario})
                atual["quantidade"] += item.quantidade

            venda = Venda(
                cliente_id=dados.cliente_id,
                data=dados.data or datetime.now(),
                status=StatusVenda.CONCLUIDA.value,
                desconto=round(dados.desconto, 2),
                observacao=dados.observacao,
            )

            subtotal = 0.0
            for produto_id, info in itens.items():
                # with_for_update: trava a linha no PostgreSQL (ignorado no SQLite)
                produto = self.db.get(Produto, produto_id, with_for_update=True)
                if not produto:
                    raise NotFoundError(f"Produto {produto_id} não encontrado.")
                if not produto.ativo:
                    raise BusinessRuleError(f"Produto '{produto.nome}' está inativo.")
                qtd = info["quantidade"]
                if produto.estoque < qtd:
                    raise BusinessRuleError(
                        f"Estoque insuficiente para '{produto.nome}': "
                        f"disponível {produto.estoque}, solicitado {qtd}."
                    )
                preco = info["preco"] if info["preco"] is not None else produto.preco_venda
                valor = round(preco * qtd, 2)
                venda.itens.append(ItemVenda(produto_id=produto.id, quantidade=qtd,
                                             preco_unitario=preco, subtotal=valor))
                produto.estoque -= qtd
                subtotal += valor

            if venda.desconto > subtotal:
                raise BusinessRuleError("O desconto não pode ser maior que o subtotal da venda.")

            venda.subtotal = round(subtotal, 2)
            venda.total = round(subtotal - venda.desconto, 2)
            self.db.add(venda)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return self.obter(venda.id)

    def cancelar(self, venda_id: int) -> Venda:
        venda = self.obter(venda_id)
        if venda.status == StatusVenda.CANCELADA:
            raise BusinessRuleError(f"A venda {venda_id} já está cancelada.")
        for item in venda.itens:
            item.produto.estoque += item.quantidade  # devolve ao estoque
        venda.status = StatusVenda.CANCELADA.value
        self.db.commit()
        return self.obter(venda_id)
