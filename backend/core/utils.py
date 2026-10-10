"""Funções utilitárias genéricas."""
import re
import unicodedata
from datetime import date, datetime, time, timedelta


def filtro_periodo(coluna, inicio: date | None, fim: date | None) -> list:
    """Gera condições SQLAlchemy para um intervalo de datas fechado [inicio, fim]."""
    filtros = []
    if inicio:
        filtros.append(coluna >= datetime.combine(inicio, time.min))
    if fim:
        filtros.append(coluna < datetime.combine(fim + timedelta(days=1), time.min))
    return filtros


def normalizar_texto(texto: str) -> str:
    """'Preço de Venda' -> 'preco_de_venda'."""
    sem_acento = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", sem_acento.lower()).strip("_")


def so_digitos(valor: str | None) -> str | None:
    if valor is None:
        return None
    digitos = re.sub(r"\D", "", str(valor))
    return digitos or None
