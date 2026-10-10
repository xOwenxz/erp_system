"""Ponto de entrada da interface: streamlit run frontend/app.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))  # permite "from frontend..." / "from backend..."

import streamlit as st  # noqa: E402

from frontend import api_client  # noqa: E402

st.set_page_config(page_title="ERP Vendas", page_icon="📊", layout="wide")

# Fundo colorido e "cards" brancos para métricas/gráficos (vale para todas as páginas)
st.markdown(
    """
    <style>
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #DCE9F7 0%, #EEF4FB 45%, #E4EEF9 100%);
        background-attachment: fixed;
    }
    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #C9DCF0 0%, #E3EDF8 100%);
        border-right: 1px solid rgba(31, 78, 120, 0.15);
    }
    [data-testid="stMetric"] {
        background: #FFFFFF;
        border-left: 5px solid #1F4E78 !important;
        border-radius: 10px;
        padding: 12px 16px;
        box-shadow: 0 2px 8px rgba(31, 78, 120, 0.10);
    }
    [data-testid="stPlotlyChart"], [data-testid="stDataFrame"] {
        background: #FFFFFF;
        border-radius: 10px;
        padding: 8px;
        box-shadow: 0 2px 8px rgba(31, 78, 120, 0.10);
    }
    h1 { color: #1F4E78; }
    </style>
    """,
    unsafe_allow_html=True,
)

VIEWS = Path(__file__).parent / "views"
paginas = {
    "Análises": [
        st.Page(VIEWS / "dashboard.py", title="Dashboard", icon="📊", default=True),
        st.Page(VIEWS / "relatorios.py", title="Relatórios", icon="📑"),
        st.Page(VIEWS / "excel.py", title="Planilhas Excel", icon="📗"),
    ],
    "Operação": [
        st.Page(VIEWS / "vendas.py", title="Vendas", icon="🛒"),
        st.Page(VIEWS / "produtos.py", title="Produtos", icon="📦"),
        st.Page(VIEWS / "clientes.py", title="Clientes", icon="👥"),
    ],
}

with st.sidebar:
    st.markdown("### 📊 ERP Vendas")
    if api_client.online():
        st.caption(f"🟢")
    else:
        st.caption(f"🔴 API ERROR")
        st.warning("Inicie o backend:\n\n`uvicorn backend.main:app --reload`")

st.navigation(paginas).run()

