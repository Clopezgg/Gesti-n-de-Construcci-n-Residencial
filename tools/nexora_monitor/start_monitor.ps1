$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Dashboard = Join-Path $PSScriptRoot "dashboard.py"
Set-Location $RepoRoot

if (-not (Test-Path $Dashboard)) {
    throw "No se encontró el monitor en: $Dashboard"
}

Write-Host ""
Write-Host "NEXORA - Monitor de avance verificable" -ForegroundColor Cyan
Write-Host "Repositorio: $RepoRoot"
Write-Host "La pantalla se abrirá en http://127.0.0.1:8765" -ForegroundColor Green
Write-Host "Mantén esta ventana abierta mientras OpenCode trabaja." -ForegroundColor Yellow
Write-Host ""

$PyLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($PyLauncher) {
    & py -3 $Dashboard
    exit $LASTEXITCODE
}

$Python = Get-Command python -ErrorAction SilentlyContinue
if ($Python) {
    & python $Dashboard
    exit $LASTEXITCODE
}

throw "Python no está disponible. Comprueba con: py --version"
