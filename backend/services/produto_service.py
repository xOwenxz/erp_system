from sqlalchemy.orm import Session

from backend.core.exceptions import ConflictError, NotFoundError
from backend.models import Produto
from backend.repositories import ProdutoRepository
from backend.schemas.produto import ProdutoCreate, ProdutoUpdate


class ProdutoService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ProdutoRepository(db)

    def listar(self, **filtros) -> list[Produto]:
        return self.repo.buscar(**filtros)

    def categorias(self) -> list[str]:
        return self.repo.categorias()

    def obter(self, produto_id: int) -> Produto:
        produto = self.repo.get(produto_id)
        if not produto:
            raise NotFoundError(f"Produto {produto_id} não encontrado.")
        return produto

    def criar(self, dados: ProdutoCreate, *, commit: bool = True) -> Produto:
        if self.repo.get_by_sku(dados.sku):
            raise ConflictError(f"Já existe um produto com o SKU '{dados.sku}'.")
        produto = self.repo.add(Produto(**dados.model_dump()))
        if commit:
            self.db.commit()
        return produto

    def atualizar(self, produto_id: int, dados: ProdutoUpdate, *, commit: bool = True) -> Produto:
        produto = self.obter(produto_id)
        valores = dados.model_dump(exclude_unset=True)
        novo_sku = valores.get("sku")
        if novo_sku and novo_sku != produto.sku and self.repo.get_by_sku(novo_sku):
            raise ConflictError(f"Já existe um produto com o SKU '{novo_sku}'.")
        self.repo.update(produto, valores)
        if commit:
            self.db.commit()
        return produto

    def desativar(self, produto_id: int) -> None:
        """Exclusão lógica: preserva o histórico de vendas."""
        produto = self.obter(produto_id)
        produto.ativo = False
        self.db.commit()
