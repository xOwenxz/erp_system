from fastapi import APIRouter, Query, status

from backend.api.deps import ProdutoSvc
from backend.schemas.produto import ProdutoCreate, ProdutoOut, ProdutoUpdate

router = APIRouter(prefix="/produtos", tags=["Produtos"])


@router.get("", response_model=list[ProdutoOut])
def listar(service: ProdutoSvc, busca: str | None = None, categoria: str | None = None,
           apenas_ativos: bool = True, skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=5000)):
    return service.listar(busca=busca, categoria=categoria, apenas_ativos=apenas_ativos, skip=skip, limit=limit)


@router.get("/categorias", response_model=list[str])
def categorias(service: ProdutoSvc):
    return service.categorias()


@router.get("/{produto_id}", response_model=ProdutoOut)
def obter(produto_id: int, service: ProdutoSvc):
    return service.obter(produto_id)


@router.post("", response_model=ProdutoOut, status_code=status.HTTP_201_CREATED)
def criar(dados: ProdutoCreate, service: ProdutoSvc):
    return service.criar(dados)


@router.put("/{produto_id}", response_model=ProdutoOut)
def atualizar(produto_id: int, dados: ProdutoUpdate, service: ProdutoSvc):
    return service.atualizar(produto_id, dados)


@router.delete("/{produto_id}", status_code=status.HTTP_204_NO_CONTENT)
def desativar(produto_id: int, service: ProdutoSvc):
    service.desativar(produto_id)
