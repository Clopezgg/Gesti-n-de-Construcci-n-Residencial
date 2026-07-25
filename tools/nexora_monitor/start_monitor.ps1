$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Server = Join-Path $PSScriptRoot "dashboard_server_v2.js"
$DashboardHtml = Join-Path $PSScriptRoot "dashboard.html"
$PanelUrl = "http://127.0.0.1:8765"
$HealthUrl = "$PanelUrl/health"
Set-Location $RepoRoot

if (-not (Test-Path $Server)) {
    throw "No se encontro el servidor del monitor: $Server"
}
if (-not (Test-Path $DashboardHtml)) {
    throw "No se encontro la pantalla del monitor: $DashboardHtml"
}

$Bun = Get-Command bun -ErrorAction SilentlyContinue
if (-not $Bun) {
    throw "Bun no esta disponible. Compruebe con: bun --version"
}

Write-Host ""
Write-Host "NEXORA Execution Monitor" -ForegroundColor Cyan
Write-Host "Repositorio: $RepoRoot"
Write-Host "Iniciando servidor Bun no bloqueante..." -ForegroundColor Yellow
Write-Host ""

$MonitorProcess = Start-Process `
    -FilePath $Bun.Source `
    -ArgumentList "`"$Server`"" `
    -PassThru `
    -NoNewWindow

$Ready = $false
for ($Attempt = 1; $Attempt -le 30; $Attempt++) {
    if ($MonitorProcess.HasExited) {
        throw "El servidor Bun termino antes de iniciar. Revise el error mostrado arriba."
    }
    try {
        $Response = Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 2
        if ($Response.StatusCode -eq 200) {
            $Ready = $true
            break
        }
    }
    catch {
        Start-Sleep -Milliseconds 500
    }
}

if (-not $Ready) {
    if (-not $MonitorProcess.HasExited) {
        Stop-Process -Id $MonitorProcess.Id -Force
    }
    throw "El monitor no respondio en $HealthUrl despues de 15 segundos."
}

Write-Host "Monitor activo: $PanelUrl" -ForegroundColor Green
Write-Host "Los datos locales cargan de inmediato; GitHub Actions se sincroniza en segundo plano." -ForegroundColor Cyan
Write-Host "Mantenga esta ventana abierta mientras OpenCode trabaja." -ForegroundColor Yellow
Start-Process $PanelUrl

Wait-Process -Id $MonitorProcess.Id
$MonitorProcess.Refresh()
exit $MonitorProcess.ExitCode
