"""Componentes e utilidades reutilizados pelas telas."""
from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

import streamlit as st

from frontend.api_client import APIError


def chamar(func: Callable, *args, sucesso: str | None = None, **kwargs) -> Any:
    """Executa uma chamada à API exibindo o erro na tela (e interrompendo a página) se falhar."""
    try:
        resultado = func(*args, **kwargs)
    except APIError as exc:
        st.error(str(exc), icon="⚠️")
        st.stop()
    if sucesso:
        st.toast(sucesso, icon="✅")
    return resultado


def tentar(func: Callable, *args, **kwargs) -> tuple[bool, Any]:
    """Como `chamar`, mas sem interromper a página (útil dentro de formulários)."""
    try:
        return True, func(*args, **kwargs)
    except APIError as exc:
        st.error(str(exc), icon="⚠️")
        return False, None


def brl(valor: float | None) -> str:
    if valor is None:
        return "-"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def numero(valor: float | int | None, casas: int = 0) -> str:
    if valor is None:
        return "-"
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


PERIODOS = ["Últimos 30 dias", "Últimos 90 dias", "Este mês", "Este ano", "Últimos 12 meses", "Tudo", "Personalizado"]


def filtro_periodo(key: str, padrao: str = "Últimos 90 dias") -> tuple[date | None, date | None]:
    """Seletor de período padrão do sistema. Retorna (inicio, fim)."""
    hoje = date.today()
    col1, col2 = st.columns([1, 2])
    escolha = col1.selectbox("Período", PERIODOS, index=PERIODOS.index(padrao), key=f"{key}_periodo")
    if escolha == "Últimos 30 dias":
        return hoje - timedelta(days=29), hoje
    if escolha == "Últimos 90 dias":
        return hoje - timedelta(days=89), hoje
    if escolha == "Este mês":
        return hoje.replace(day=1), hoje
    if escolha == "Este ano":
        return hoje.replace(month=1, day=1), hoje
    if escolha == "Últimos 12 meses":
        return hoje - timedelta(days=364), hoje
    if escolha == "Tudo":
        return None, None
    intervalo = col2.date_input("Intervalo", value=(hoje - timedelta(days=29), hoje), format="DD/MM/YYYY",
                                key=f"{key}_intervalo")
    if isinstance(intervalo, tuple) and len(intervalo) == 2:
        return intervalo
    st.info("Selecione a data inicial e a final.")
    st.stop()


def limpar_cache():
    st.cache_data.clear()

