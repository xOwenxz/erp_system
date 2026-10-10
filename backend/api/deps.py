"""Injeção de dependências: cada rota recebe o serviço já com a sessão do banco."""
from typing import Annotated

from fastapi import Depends, Response
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.services.cliente_service import ClienteService
from backend.services.dashboard_service import DashboardService
from backend.services.excel_service import ExcelService
from backend.services.produto_service import ProdutoService
from backend.services.relatorio_service import RelatorioService
from backend.services.venda_service import VendaService

DbSession = Annotated[Session, Depends(get_db)]

ProdutoSvc = Annotated[ProdutoService, Depends(lambda db=Depends(get_db): ProdutoService(db))]
ClienteSvc = Annotated[ClienteService, Depends(lambda db=Depends(get_db): ClienteService(db))]
VendaSvc = Annotated[VendaService, Depends(lambda db=Depends(get_db): VendaService(db))]
DashboardSvc = Annotated[DashboardService, Depends(lambda db=Depends(get_db): DashboardService(db))]
RelatorioSvc = Annotated[RelatorioService, Depends(lambda db=Depends(get_db): RelatorioService(db))]
ExcelSvc = Annotated[ExcelService, Depends(lambda db=Depends(get_db): ExcelService(db))]


def arquivo_response(conteudo: bytes, nome_arquivo: str, media_type: str) -> Response:
    return Response(
        content=conteudo,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}"'},
    )
