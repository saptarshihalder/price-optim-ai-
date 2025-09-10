param(
  [int]$Port = 8000
)

$ErrorActionPreference = 'Stop'

Write-Host "[backend] Ensuring virtualenv and dependencies..." -ForegroundColor Cyan
Set-Location "$PSScriptRoot/..\backend"

if (-not (Test-Path ".venv")) {
  $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
  if ($pyLauncher) {
    & py -3 -m venv .venv
  } else {
    Write-Host "[backend] 'py' launcher not found. Using 'python' to create venv..." -ForegroundColor Yellow
    & python -m venv .venv
  }
}

& .\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip | Out-Null
pip install -r requirements.txt

Write-Host "[backend] Starting Uvicorn on port $Port..." -ForegroundColor Green
# We are already in the backend folder, so module path is just 'main:app'
python -m uvicorn main:app --reload --port $Port
