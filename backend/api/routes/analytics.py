from datetime import date
from typing import Literal

from fastapi import APIRouter, File, Query, UploadFile

from backend.api.deps import DashboardSvc, ExcelSvc, RelatorioSvc, arquivo_response
from backend.core.config import settings
from backend.core.exceptions import BusinessRuleError
from backend.core.exporters import MEDIA_CSV, MEDIA_XLSX, to_csv, to_records, to_xlsx
from backend.schemas.analytics import (
    Agrupamento, DashboardOut, EntidadeImportacaoOut, ExcelAnaliseOut, ImportResultado, RelatorioDados,
    RelatorioInfo,
)

# ---------------------------------------------------------------- Dashboard
dashboard_router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@dashboard_router.get("", response_model=DashboardOut)
def dashboard(service: DashboardSvc, inicio: date | None = None, fim: date | None = None,
              agrupamento: Agrupamento = "mes", limite: int = Query(10, ge=1, le=100)):
    return service.gerar(inicio=inicio, fim=fim, agrupamento=agrupamento, limite=limite)


# ---------------------------------------------------------------- Relatórios
relatorios_router = APIRouter(prefix="/relatorios", tags=["Relatórios"])


@relatorios_router.get("", response_model=list[RelatorioInfo])
def listar_relatorios(service: RelatorioSvc):
    return [RelatorioInfo(nome=r.nome, titulo=r.titulo, descricao=r.descricao, usa_periodo=r.usa_periodo)
            for r in service.listar()]


@relatorios_router.get("/{nome}", response_model=None)
def gerar_relatorio(nome: str, service: RelatorioSvc, inicio: date | None = None, fim: date | None = None,
                    formato: Literal["json", "xlsx", "csv"] = "json"):
    definicao, df = service.gerar(nome, inicio, fim)
    if formato == "xlsx":
        return arquivo_response(to_xlsx({definicao.titulo: df}), f"relatorio_{nome}.xlsx", MEDIA_XLSX)
    if formato == "csv":
        return arquivo_response(to_csv(df), f"relatorio_{nome}.csv", MEDIA_CSV)
    return RelatorioDados(nome=definicao.nome, titulo=definicao.titulo, colunas=[str(c) for c in df.columns],
                          linhas=to_records(df), total_linhas=len(df))


# ---------------------------------------------------------------- Excel
excel_router = APIRouter(prefix="/excel", tags=["Excel"])


def _ler_upload(arquivo: UploadFile) -> bytes:
    conteudo = arquivo.file.read()
    if not conteudo:
        raise BusinessRuleError("Arquivo vazio.")
    if len(conteudo) > settings.excel_max_file_mb * 1024 * 1024:
        raise BusinessRuleError(f"Arquivo maior que o limite de {settings.excel_max_file_mb} MB.")
    return conteudo


@excel_router.get("/entidades", response_model=list[EntidadeImportacaoOut])
def entidades(service: ExcelSvc):
    return service.entidades()


@excel_router.post("/analisar", response_model=ExcelAnaliseOut)
def analisar(service: ExcelSvc, arquivo: UploadFile = File(...), aba: str | None = None,
             max_linhas: int | None = Query(None, ge=1, le=100_000)):
    return service.analisar(_ler_upload(arquivo), arquivo.filename, aba, max_linhas)


@excel_router.post("/importar/{entidade}", response_model=ImportResultado)
def importar(entidade: str, service: ExcelSvc, arquivo: UploadFile = File(...), aba: str | None = None):
    return service.importar(entidade, _ler_upload(arquivo), arquivo.filename, aba)


@excel_router.get("/modelos/{entidade}")
def modelo(entidade: str, service: ExcelSvc):
    return arquivo_response(service.gerar_modelo(entidade), f"modelo_{entidade}.xlsx", MEDIA_XLSX)
