$ErrorActionPreference = 'Stop'

Write-Host "[frontend] Installing dependencies (if needed) and starting Vite dev server..." -ForegroundColor Green
Set-Location "$PSScriptRoot/.."

if (-not (Test-Path "node_modules")) {
  npm install
}

npm run dev

