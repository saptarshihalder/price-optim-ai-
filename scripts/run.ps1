$ErrorActionPreference = 'Stop'

param(
  [int]$ApiPort = 8000
)

Write-Host "Booting backend and frontend..." -ForegroundColor Cyan

# Start backend in a background job
$backendScript = Join-Path $PSScriptRoot 'run-backend.ps1'
Start-Job -ScriptBlock {
  param($scriptPath, $port)
  & powershell -ExecutionPolicy Bypass -File $scriptPath -Port $port
} -ArgumentList $backendScript, $ApiPort | Out-Null

Start-Sleep -Seconds 2

# Start frontend (blocks)
$frontendScript = Join-Path $PSScriptRoot 'run-frontend.ps1'
& powershell -ExecutionPolicy Bypass -File $frontendScript

