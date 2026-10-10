from fastapi import APIRouter, Query, status

from backend.api.deps import ClienteSvc
from backend.schemas.cliente import ClienteCreate, ClienteOut, ClienteUpdate

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.get("", response_model=list[ClienteOut])
def listar(service: ClienteSvc, busca: str | None = None, apenas_ativos: bool = True,
           skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=5000)):
    return service.listar(busca=busca, apenas_ativos=apenas_ativos, skip=skip, limit=limit)


@router.get("/{cliente_id}", response_model=ClienteOut)
def obter(cliente_id: int, service: ClienteSvc):
    return service.obter(cliente_id)


@router.post("", response_model=ClienteOut, status_code=status.HTTP_201_CREATED)
def criar(dados: ClienteCreate, service: ClienteSvc):
    return service.criar(dados)


@router.put("/{cliente_id}", response_model=ClienteOut)
def atualizar(cliente_id: int, dados: ClienteUpdate, service: ClienteSvc):
    return service.atualizar(cliente_id, dados)


@router.delete("/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
def desativar(cliente_id: int, service: ClienteSvc):
    service.desativar(cliente_id)
