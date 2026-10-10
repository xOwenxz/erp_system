from datetime import date

from fastapi import APIRouter, Query, status

from backend.api.deps import VendaSvc
from backend.models import StatusVenda
from backend.schemas.venda import VendaCreate, VendaOut

router = APIRouter(prefix="/vendas", tags=["Vendas"])


@router.get("", response_model=list[VendaOut])
def listar(service: VendaSvc, inicio: date | None = None, fim: date | None = None,
           status_venda: StatusVenda | None = Query(None, alias="status"), cliente_id: int | None = None,
           skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=5000)):
    return service.listar(inicio=inicio, fim=fim, status=status_venda, cliente_id=cliente_id,
                          skip=skip, limit=limit)


@router.get("/{venda_id}", response_model=VendaOut)
def obter(venda_id: int, service: VendaSvc):
    return service.obter(venda_id)


@router.post("", response_model=VendaOut, status_code=status.HTTP_201_CREATED)
def criar(dados: VendaCreate, service: VendaSvc):
    return service.criar(dados)


@router.post("/{venda_id}/cancelar", response_model=VendaOut)
def cancelar(venda_id: int, service: VendaSvc):
    return service.cancelar(venda_id)
