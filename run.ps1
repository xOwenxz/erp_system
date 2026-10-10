<#
.SYNOPSIS
  Inicia o ERP (API + interface). Uso: .\run.ps1   |   .\run.ps1 -Seed (gera dados de exemplo antes)
#>
param([switch]$Seed)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $py)) {
    Write-Host "Criando ambiente virtual..." -ForegroundColor Cyan
    py -3.12 -m venv .venv
    & $py -m pip install -q --upgrade pip
    & $py -m pip install -q -r requirements-dev.txt
}

if ($Seed) { & $py -m scripts.seed --reset }

Write-Host "Iniciando API em http://127.0.0.1:8000 (docs: /docs)" -ForegroundColor Green
$api = Start-Process $py -ArgumentList "-m", "uvicorn", "backend.main:app", "--port", "8000" -PassThru -NoNewWindow

try {
    Write-Host "Iniciando interface em http://localhost:8501" -ForegroundColor Green
    & $py -m streamlit run frontend/app.py
}
finally {
    if ($api -and -not $api.HasExited) { Stop-Process -Id $api.Id -Force }
}

