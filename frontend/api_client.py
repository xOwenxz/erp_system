"""Cliente HTTP da API. Toda comunicação do frontend com o backend passa por aqui."""
from typing import Any

import requests
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.core.config import BASE_DIR


class _FrontendSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", env_file_encoding="utf-8", extra="ignore")
    erp_api_url: str = "http://127.0.0.1:8000/api/v1"


API_URL = _FrontendSettings().erp_api_url.rstrip("/")
TIMEOUT = 120


class APIError(Exception):
    """Erro retornado pela API (ou falha de conexão), com mensagem amigável."""


def _detalhe(resp: requests.Response) -> str:
    try:
        detail = resp.json().get("detail")
    except ValueError:
        return resp.text or f"Erro {resp.status_code}"
    if isinstance(detail, list):  # erros de validação do FastAPI/Pydantic
        partes = []
        for e in detail:
            campo = ".".join(str(p) for p in e.get("loc", [])[1:])
            partes.append(f"{campo}: {e.get('msg')}" if campo else str(e.get("msg")))
        return "; ".join(partes)
    return str(detail or f"Erro {resp.status_code}")


def _request(method: str, path: str, **kwargs) -> requests.Response:
    try:
        resp = requests.request(method, f"{API_URL}{path}", timeout=TIMEOUT, **kwargs)
    except requests.ConnectionError:
        raise APIError(f"Não foi possível conectar à API em {API_URL}. Verifique se o backend está rodando.") from None
    except requests.Timeout:
        raise APIError("A API demorou demais para responder.") from None
    if resp.status_code >= 400:
        raise APIError(_detalhe(resp))
    return resp


def _limpar(params: dict | None) -> dict | None:
    return {k: v for k, v in params.items() if v is not None} if params else None


def get(path: str, **params) -> Any:
    return _request("GET", path, params=_limpar(params)).json()


def get_bytes(path: str, **params) -> bytes:
    return _request("GET", path, params=_limpar(params)).content


def post(path: str, json: dict | None = None, files: dict | None = None, **params) -> Any:
    resp = _request("POST", path, json=json, files=files, params=_limpar(params))
    return resp.json() if resp.content else None


def put(path: str, json: dict) -> Any:
    return _request("PUT", path, json=json).json()


def delete(path: str) -> None:
    _request("DELETE", path)


def online() -> bool:
    try:
        return requests.get(API_URL.rsplit("/api/", 1)[0] + "/health", timeout=3).ok
    except requests.RequestException:
        return False

