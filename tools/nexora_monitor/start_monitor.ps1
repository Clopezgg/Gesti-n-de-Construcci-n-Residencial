$ErrorActionPreference = "Stop"

[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [System.Text.UTF8Encoding]::new()
try { chcp 65001 | Out-Null } catch {}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Dashboard = Join-Path $PSScriptRoot "dashboard.js"
Set-Location $RepoRoot

if (-not (Test-Path $Dashboard)) {
    throw "No se encontró el monitor en: $Dashboard"
}

$Bun = Get-Command bun -ErrorAction SilentlyContinue
if (-not $Bun) {
    throw "Bun no está disponible. Comprueba con: bun --version"
}

Write-Host ""
Write-Host "NEXORA Execution Monitor" -ForegroundColor Cyan
Write-Host "Repositorio: $RepoRoot"
Write-Host "Panel: http://127.0.0.1:8765" -ForegroundColor Green
Write-Host "Mantén esta ventana abierta mientras OpenCode trabaja." -ForegroundColor Yellow
Write-Host ""

Start-Process "http://127.0.0.1:8765"
& bun $Dashboard
exit $LASTEXITCODE
