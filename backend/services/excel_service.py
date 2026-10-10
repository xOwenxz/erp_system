"""Leitura, análise e importação de planilhas Excel/CSV."""
import json
import math
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd
from pandas.api import types as ptypes
from pydantic import ValidationError
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.exceptions import BusinessRuleError, DomainError, NotFoundError
from backend.core.exporters import to_xlsx
from backend.core.utils import normalizar_texto, so_digitos
from backend.repositories import ClienteRepository, ProdutoRepository
from backend.schemas.analytics import (
    CampoImportacaoOut, ColunaPerfil, EntidadeImportacaoOut, ExcelAnaliseOut, ImportErro, ImportResultado,
)
from backend.schemas.cliente import ClienteCreate, ClienteUpdate
from backend.schemas.produto import ProdutoCreate, ProdutoUpdate
from backend.services.cliente_service import ClienteService
from backend.services.produto_service import ProdutoService

EXTENSOES_EXCEL = {".xlsx", ".xlsm"}
EXTENSOES_CSV = {".csv"}


# ----------------------------------------------------------------------------
# Configuração das entidades importáveis
# ----------------------------------------------------------------------------
@dataclass(frozen=True)
class CampoImportacao:
    nome: str
    tipo: str  # texto | decimal | inteiro
    obrigatorio: bool = False
    aliases: tuple[str, ...] = field(default_factory=tuple)


ENTIDADES: dict[str, list[CampoImportacao]] = {
    "produtos": [
        CampoImportacao("sku", "texto", True, ("codigo", "cod", "referencia", "ref", "codigo_produto")),
        CampoImportacao("nome", "texto", True, ("produto", "descricao", "nome_produto")),
        CampoImportacao("categoria", "texto", False, ("grupo", "familia")),
        CampoImportacao("preco_custo", "decimal", False, ("custo", "valor_custo", "preco_de_custo")),
        CampoImportacao("preco_venda", "decimal", True, ("preco", "valor", "valor_venda", "preco_de_venda", "preco_unitario")),
        CampoImportacao("estoque", "inteiro", False, ("quantidade", "qtd", "saldo", "estoque_atual")),
        CampoImportacao("estoque_minimo", "inteiro", False, ("minimo", "estoque_min")),
    ],
    "clientes": [
        CampoImportacao("nome", "texto", True, ("cliente", "razao_social", "nome_cliente")),
        CampoImportacao("documento", "texto", False, ("cpf", "cnpj", "cpf_cnpj", "cpf_cnpj_")),
        CampoImportacao("email", "texto", False, ("e_mail", "mail")),
        CampoImportacao("telefone", "texto", False, ("celular", "fone", "whatsapp", "contato")),
        CampoImportacao("cidade", "texto", False, ("municipio",)),
        CampoImportacao("uf", "texto", False, ("estado",)),
    ],
}

EXEMPLOS: dict[str, list[dict[str, Any]]] = {
    "produtos": [
        {"sku": "CAD-001", "nome": "Cadeira de Escritório", "categoria": "Móveis",
         "preco_custo": 250.0, "preco_venda": 499.9, "estoque": 20, "estoque_minimo": 5},
        {"sku": "MOU-010", "nome": "Mouse sem fio", "categoria": "Informática",
         "preco_custo": 35.0, "preco_venda": 79.9, "estoque": 150, "estoque_minimo": 30},
    ],
    "clientes": [
        {"nome": "Maria Souza", "documento": "123.456.789-09", "email": "maria@email.com",
         "telefone": "(11) 99999-0000", "cidade": "São Paulo", "uf": "SP"},
        {"nome": "Empresa Exemplo LTDA", "documento": "12.345.678/0001-90", "email": "contato@exemplo.com",
         "telefone": "(31) 3333-0000", "cidade": "Belo Horizonte", "uf": "MG"},
    ],
}


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def _eh_nulo(valor: Any) -> bool:
    if valor is None:
        return True
    try:
        return bool(pd.isna(valor))
    except (TypeError, ValueError):
        return False


def _converter(valor: Any, tipo: str) -> Any:
    """Converte o valor da célula para o tipo esperado (aceita formato brasileiro '1.234,56')."""
    if _eh_nulo(valor):
        return None
    if tipo == "texto":
        if isinstance(valor, float) and valor.is_integer():
            valor = int(valor)  # 12345.0 -> "12345" (códigos lidos como número)
        texto = str(valor).strip()
        return texto or None
    if tipo in ("decimal", "inteiro"):
        if isinstance(valor, str):
            s = valor.strip().replace("R$", "").replace(" ", "")
            if not s:
                return None
            if "," in s:
                s = s.replace(".", "").replace(",", ".")
            try:
                numero = float(s)
            except ValueError:
                raise ValueError(f"valor numérico inválido: '{valor}'") from None
        else:
            numero = float(valor)
        if math.isnan(numero):
            return None
        if tipo == "inteiro":
            if not numero.is_integer():
                raise ValueError(f"esperado número inteiro, recebido '{valor}'")
            return int(numero)
        return round(numero, 2)
    return valor


def _json_safe(valor: Any) -> Any:
    if _eh_nulo(valor):
        return None
    if hasattr(valor, "isoformat"):
        return valor.isoformat()
    if hasattr(valor, "item"):  # tipos numpy
        return valor.item()
    return valor


def _tipo_coluna(serie: pd.Series) -> str:
    if ptypes.is_bool_dtype(serie):
        return "booleano"
    if ptypes.is_numeric_dtype(serie):
        return "numérico"
    if ptypes.is_datetime64_any_dtype(serie):
        return "data"
    return "texto"


def _colunas_unicas(colunas) -> list[str]:
    vistos: dict[str, int] = {}
    resultado = []
    for c in colunas:
        nome = str(c).strip() or "coluna"
        if nome in vistos:
            vistos[nome] += 1
            nome = f"{nome}_{vistos[nome]}"
        else:
            vistos[nome] = 0
        resultado.append(nome)
    return resultado


def _formatar_validacao(erro: ValidationError) -> str:
    partes = []
    for e in erro.errors():
        campo = ".".join(str(p) for p in e.get("loc", ()))
        partes.append(f"{campo}: {e.get('msg')}" if campo else str(e.get("msg")))
    return "; ".join(partes)


# ----------------------------------------------------------------------------
class ExcelService:
    def __init__(self, db: Session | None = None):
        self.db = db

    # ---------- Leitura ----------
    @staticmethod
    def _extensao(nome: str | None) -> str:
        ext = Path(nome or "").suffix.lower()
        if ext not in EXTENSOES_EXCEL | EXTENSOES_CSV:
            raise BusinessRuleError("Formato não suportado. Envie um arquivo .xlsx, .xlsm ou .csv.")
        return ext

    @staticmethod
    def _ler_csv(conteudo: bytes) -> pd.DataFrame:
        for encoding in ("utf-8-sig", "latin-1"):
            try:
                return pd.read_csv(BytesIO(conteudo), sep=None, engine="python", encoding=encoding)
            except UnicodeDecodeError:
                continue
        raise BusinessRuleError("Não foi possível identificar a codificação do CSV.")

    def ler(self, conteudo: bytes, nome: str, aba: str | None = None) -> tuple[pd.DataFrame, list[str], str]:
        ext = self._extensao(nome)
        try:
            if ext in EXTENSOES_CSV:
                abas = ["dados"]
                aba = aba or abas[0]
                df = self._ler_csv(conteudo)
            else:
                arquivo = pd.ExcelFile(BytesIO(conteudo), engine="openpyxl")
                abas = list(arquivo.sheet_names)
                aba = aba or abas[0]
                if aba not in abas:
                    raise BusinessRuleError(f"Aba '{aba}' não encontrada. Abas disponíveis: {', '.join(abas)}")
                df = arquivo.parse(sheet_name=aba)
        except DomainError:
            raise
        except Exception as exc:  # arquivo corrompido, senha, etc.
            raise BusinessRuleError(f"Não foi possível ler o arquivo: {exc}") from exc

        df.columns = _colunas_unicas(df.columns)
        df = df.dropna(how="all")  # mantém o índice original -> nº da linha correto nos erros
        return df, abas, aba

    # ---------- Análise ----------
    def analisar(self, conteudo: bytes, nome: str, aba: str | None = None,
                 max_linhas: int | None = None) -> ExcelAnaliseOut:
        max_linhas = max_linhas or settings.excel_max_rows
        df, abas, aba = self.ler(conteudo, nome, aba)

        colunas = []
        for c in df.columns:
            serie = df[c]
            nao_nulos = serie.dropna()
            colunas.append(ColunaPerfil(
                nome=c,
                tipo=_tipo_coluna(serie),
                nao_nulos=int(serie.notna().sum()),
                nulos=int(serie.isna().sum()),
                unicos=int(serie.nunique(dropna=True)),
                exemplo=_json_safe(nao_nulos.iloc[0]) if not nao_nulos.empty else None,
            ))

        numericas = df.select_dtypes(include="number")
        estatisticas = json.loads(numericas.describe().round(4).to_json()) if not numericas.empty else {}
        dados = json.loads(df.head(max_linhas).to_json(orient="records", date_format="iso", force_ascii=False))

        return ExcelAnaliseOut(
            arquivo=nome, abas=abas, aba=aba,
            total_linhas=len(df), total_colunas=len(df.columns),
            colunas=colunas, estatisticas=estatisticas,
            dados=dados, truncado=len(df) > max_linhas,
        )

    # ---------- Importação ----------
    @staticmethod
    def entidades() -> list[EntidadeImportacaoOut]:
        return [
            EntidadeImportacaoOut(entidade=nome, campos=[
                CampoImportacaoOut(nome=c.nome, tipo=c.tipo, obrigatorio=c.obrigatorio, aliases=list(c.aliases))
                for c in campos
            ])
            for nome, campos in ENTIDADES.items()
        ]

    @staticmethod
    def _campos(entidade: str) -> list[CampoImportacao]:
        if entidade not in ENTIDADES:
            raise NotFoundError(f"Entidade '{entidade}' não suporta importação. Opções: {', '.join(ENTIDADES)}")
        return ENTIDADES[entidade]

    @staticmethod
    def _mapear_colunas(colunas, campos: list[CampoImportacao]) -> dict[str, str]:
        """Retorna {campo_do_sistema: coluna_da_planilha} reconhecendo sinônimos."""
        lookup: dict[str, str] = {}
        for campo in campos:
            for alias in (campo.nome, *campo.aliases):
                lookup.setdefault(normalizar_texto(alias), campo.nome)
        mapa: dict[str, str] = {}
        for coluna in colunas:
            campo = lookup.get(normalizar_texto(coluna))
            if campo and campo not in mapa:
                mapa[campo] = coluna
        return mapa

    def importar(self, entidade: str, conteudo: bytes, nome: str, aba: str | None = None) -> ImportResultado:
        if self.db is None:
            raise RuntimeError("ExcelService.importar requer uma sessão de banco.")
        campos = self._campos(entidade)
        df, _, _ = self.ler(conteudo, nome, aba)
        mapa = self._mapear_colunas(df.columns, campos)

        faltando = [c.nome for c in campos if c.obrigatorio and c.nome not in mapa]
        if faltando:
            raise BusinessRuleError(
                f"Colunas obrigatórias ausentes: {', '.join(faltando)}. "
                f"Colunas encontradas: {', '.join(map(str, df.columns))}."
            )

        tipos = {c.nome: c.tipo for c in campos}
        upsert = {"produtos": self._upsert_produto, "clientes": self._upsert_cliente}[entidade]
        resultado = ImportResultado(entidade=entidade, total_linhas=len(df))

        try:
            for idx, row in df.iterrows():
                linha = int(idx) + 2  # +1 cabeçalho, +1 índice começa em 0
                try:
                    dados = {campo: _converter(row[col], tipos[campo]) for campo, col in mapa.items()}
                    if all(v is None for v in dados.values()):
                        continue
                    acao = upsert({k: v for k, v in dados.items() if v is not None})
                except ValidationError as exc:
                    resultado.erros.append(ImportErro(linha=linha, erro=_formatar_validacao(exc)))
                except (DomainError, ValueError) as exc:
                    resultado.erros.append(ImportErro(linha=linha, erro=getattr(exc, "message", str(exc))))
                else:
                    if acao == "inserido":
                        resultado.inseridos += 1
                    else:
                        resultado.atualizados += 1
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return resultado

    def _upsert_produto(self, dados: dict) -> str:
        service = ProdutoService(self.db)
        existente = ProdutoRepository(self.db).get_by_sku(str(dados.get("sku", "")).strip())
        if existente:
            service.atualizar(existente.id, ProdutoUpdate(**dados), commit=False)
            return "atualizado"
        service.criar(ProdutoCreate(**dados), commit=False)
        return "inserido"

    def _upsert_cliente(self, dados: dict) -> str:
        service = ClienteService(self.db)
        repo = ClienteRepository(self.db)
        existente = None
        if documento := so_digitos(dados.get("documento")):
            existente = repo.get_by_documento(documento)
        if not existente and dados.get("email"):
            existente = repo.get_by_email(dados["email"])
        if existente:
            service.atualizar(existente.id, ClienteUpdate(**dados), commit=False)
            return "atualizado"
        service.criar(ClienteCreate(**dados), commit=False)
        return "inserido"

    # ---------- Modelos ----------
    def gerar_modelo(self, entidade: str) -> bytes:
        campos = self._campos(entidade)
        dados = pd.DataFrame(EXEMPLOS.get(entidade, []), columns=[c.nome for c in campos])
        instrucoes = pd.DataFrame([
            {"Coluna": c.nome, "Obrigatória": "Sim" if c.obrigatorio else "Não", "Tipo": c.tipo,
             "Também aceita": ", ".join(c.aliases)}
            for c in campos
        ])
        return to_xlsx({entidade: dados, "instrucoes": instrucoes})
