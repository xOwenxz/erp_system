"""Agrega todos os routers da API v1. Novos módulos são registrados aqui."""
from fastapi import APIRouter

from backend.api.routes import clientes, produtos, vendas
from backend.api.routes.analytics import dashboard_router, excel_router, relatorios_router

api_router = APIRouter()
api_router.include_router(dashboard_router)
api_router.include_router(relatorios_router)
api_router.include_router(excel_router)
api_router.include_router(vendas.router)
api_router.include_router(produtos.router)
api_router.include_router(clientes.router)
