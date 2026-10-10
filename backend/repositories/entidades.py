from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from backend.core.utils import filtro_periodo
from backend.models import Cliente, ItemVenda, Produto, Venda
from backend.repositories.base import BaseRepository


class ProdutoRepository(BaseRepository[Produto]):
    model = Produto

    def get_by_sku(self, sku: str) -> Produto | None:
        return self.db.scalar(select(Produto).where(Produto.sku == sku))

    def buscar(self, *, busca: str | None = None, categoria: str | None = None,
               apenas_ativos: bool = True, skip: int = 0, limit: int = 100) -> list[Produto]:
        filtros = []
        if busca:
            termo = f"%{busca}%"
            filtros.append(or_(Produto.nome.ilike(termo), Produto.sku.ilike(termo)))
        if categoria:
            filtros.append(Produto.categoria == categoria)
        if apenas_ativos:
            filtros.append(Produto.ativo.is_(True))
        return self.list(filtros=filtros, skip=skip, limit=limit, ordem=Produto.nome)

    def categorias(self) -> list[str]:
        stmt = (select(Produto.categoria).where(Produto.categoria.is_not(None))
                .distinct().order_by(Produto.categoria))
        return list(self.db.scalars(stmt))

    def estoque_baixo(self) -> list[Produto]:
        stmt = (select(Produto)
                .where(Produto.ativo.is_(True), Produto.estoque <= Produto.estoque_minimo)
                .order_by(Produto.estoque))
        return list(self.db.scalars(stmt))


class ClienteRepository(BaseRepository[Cliente]):
    model = Cliente

    def get_by_documento(self, documento: str) -> Cliente | None:
        return self.db.scalar(select(Cliente).where(Cliente.documento == documento))

    def get_by_email(self, email: str) -> Cliente | None:
        return self.db.scalar(select(Cliente).where(Cliente.email == email.lower()))

    def buscar(self, *, busca: str | None = None, apenas_ativos: bool = True,
               skip: int = 0, limit: int = 100) -> list[Cliente]:
        filtros = []
        if busca:
            termo = f"%{busca}%"
            filtros.append(or_(Cliente.nome.ilike(termo), Cliente.documento.ilike(termo),
                               Cliente.email.ilike(termo)))
        if apenas_ativos:
            filtros.append(Cliente.ativo.is_(True))
        return self.list(filtros=filtros, skip=skip, limit=limit, ordem=Cliente.nome)


class VendaRepository(BaseRepository[Venda]):
    model = Venda

    def _com_relacoes(self):
        return select(Venda).options(
            selectinload(Venda.cliente),
            selectinload(Venda.itens).selectinload(ItemVenda.produto),
        )

    def get_completa(self, venda_id: int) -> Venda | None:
        stmt = (self._com_relacoes().where(Venda.id == venda_id)
                .execution_options(populate_existing=True))
        return self.db.scalar(stmt)

    def buscar(self, *, inicio: date | None = None, fim: date | None = None,
               status: str | None = None, cliente_id: int | None = None,
               skip: int = 0, limit: int = 100) -> list[Venda]:
        filtros = filtro_periodo(Venda.data, inicio, fim)
        if status:
            filtros.append(Venda.status == status)
        if cliente_id:
            filtros.append(Venda.cliente_id == cliente_id)
        stmt = (self._com_relacoes().where(*filtros)
                .order_by(Venda.data.desc(), Venda.id.desc()).offset(skip).limit(limit))
        return list(self.db.scalars(stmt))
