$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $RepoRoot

$Branch = (git branch --show-current).Trim()
if ($Branch -ne "nexora-continuidad-total") {
    throw "Rama incorrecta: $Branch. Debe ser nexora-continuidad-total."
}

$Dirty = git status --porcelain
if ($Dirty) {
    Write-Host "Hay cambios locales sin guardar. No se hará pull ni se iniciará otra ejecución." -ForegroundColor Red
    git status --short
    throw "Guarda o revisa los cambios locales antes de continuar."
}

Write-Host "Actualizando nexora-continuidad-total mediante fast-forward..." -ForegroundColor Cyan
git pull --ff-only origin nexora-continuidad-total
if ($LASTEXITCODE -ne 0) {
    throw "git pull falló. No se inició OpenCode."
}

$MonitorScript = Join-Path $PSScriptRoot "start_monitor.ps1"
$MonitorArgs = "-NoExit -ExecutionPolicy Bypass -File `"$MonitorScript`""
Start-Process powershell.exe -ArgumentList $MonitorArgs
Start-Sleep -Seconds 2

$OpenCode = Get-Command opencode -ErrorAction SilentlyContinue
if (-not $OpenCode) {
    throw "OpenCode no está disponible en PATH. Comprueba con: opencode --version"
}

$Prompt = @"
Lee AGENTS.md, docs/nexora/ORDEN_MAESTRA_FINALIZACION.md y docs/nexora/AUDITORIA_CORRECCION_FINAL.md. Continúa automáticamente la corrección final punto por punto sobre nexora-continuidad-total. Actualiza docs/nexora/LIVE_PROGRESS.json antes y después de cada prueba para alimentar el monitor. Corrige todos los workflows fallidos, audita las 166 filas individualmente, prueba, haz commits semánticos y push únicamente a origin/nexora-continuidad-total. No fusiones, no crees tags y no despliegues. Detente solo ante un bloqueo real o una acción expresamente prohibida.
"@

Write-Host ""
Write-Host "Monitor abierto. Iniciando OpenCode en modo automático protegido..." -ForegroundColor Green
Write-Host ""
& opencode run --auto $Prompt

Write-Host ""
Write-Host "La ejecución de OpenCode terminó o se detuvo. El monitor permanece abierto en la otra ventana." -ForegroundColor Yellow
