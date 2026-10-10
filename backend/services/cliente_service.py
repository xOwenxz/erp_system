from sqlalchemy.orm import Session

from backend.core.exceptions import ConflictError, NotFoundError
from backend.models import Cliente
from backend.repositories import ClienteRepository
from backend.schemas.cliente import ClienteCreate, ClienteUpdate


class ClienteService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ClienteRepository(db)

    def listar(self, **filtros) -> list[Cliente]:
        return self.repo.buscar(**filtros)

    def obter(self, cliente_id: int) -> Cliente:
        cliente = self.repo.get(cliente_id)
        if not cliente:
            raise NotFoundError(f"Cliente {cliente_id} não encontrado.")
        return cliente

    def _validar_documento(self, documento: str | None, ignorar_id: int | None = None) -> None:
        if not documento:
            return
        existente = self.repo.get_by_documento(documento)
        if existente and existente.id != ignorar_id:
            raise ConflictError(f"Já existe um cliente com o documento '{documento}'.")

    def criar(self, dados: ClienteCreate, *, commit: bool = True) -> Cliente:
        self._validar_documento(dados.documento)
        cliente = self.repo.add(Cliente(**dados.model_dump()))
        if commit:
            self.db.commit()
        return cliente

    def atualizar(self, cliente_id: int, dados: ClienteUpdate, *, commit: bool = True) -> Cliente:
        cliente = self.obter(cliente_id)
        valores = dados.model_dump(exclude_unset=True)
        self._validar_documento(valores.get("documento"), ignorar_id=cliente.id)
        self.repo.update(cliente, valores)
        if commit:
            self.db.commit()
        return cliente

    def desativar(self, cliente_id: int) -> None:
        cliente = self.obter(cliente_id)
        cliente.ativo = False
        self.db.commit()
