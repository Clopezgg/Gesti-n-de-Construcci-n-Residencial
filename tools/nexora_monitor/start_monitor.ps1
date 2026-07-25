$ErrorActionPreference = "Stop"

[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [System.Text.UTF8Encoding]::new()
try { chcp 65001 | Out-Null } catch {}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Server = Join-Path $PSScriptRoot "dashboard_server_v3.js"
$DashboardHtml = Join-Path $PSScriptRoot "dashboard.html"
$AuditModel = Join-Path $PSScriptRoot "audit_model.js"
$AuditCli = Join-Path $PSScriptRoot "audit_cli.js"
$PanelUrl = "http://127.0.0.1:8765"
$HealthUrl = "$PanelUrl/health"
Set-Location $RepoRoot

$RequiredFiles = @($Server, $DashboardHtml, $AuditModel, $AuditCli)
foreach ($RequiredFile in $RequiredFiles) {
    if (-not (Test-Path $RequiredFile)) {
        throw "No se encontro un componente obligatorio del monitor: $RequiredFile"
    }
}

$Bun = Get-Command bun -ErrorAction SilentlyContinue
if (-not $Bun) {
    throw "Bun no esta disponible. Compruebe con: bun --version"
}

Write-Host ""
Write-Host "NEXORA - Auditoria por Capas" -ForegroundColor Cyan
Write-Host "Repositorio: $RepoRoot"
Write-Host "Iniciando servidor Bun v3 no bloqueante..." -ForegroundColor Yellow
Write-Host "La matriz documental no certifica por si sola." -ForegroundColor Yellow
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
Write-Host "Auditoria y certificacion se calculan por separado." -ForegroundColor Cyan
Write-Host "Mantenga esta ventana abierta mientras OpenCode trabaja." -ForegroundColor Yellow
Start-Process $PanelUrl

Wait-Process -Id $MonitorProcess.Id
$MonitorProcess.Refresh()
exit $MonitorProcess.ExitCode
