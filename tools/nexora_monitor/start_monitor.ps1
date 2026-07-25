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
$RuntimeDir = Join-Path $RepoRoot ".nexora-monitor"
$SupervisorPath = Join-Path $RuntimeDir "monitor-supervisor.json"
$WatchdogLog = Join-Path $RuntimeDir "monitor-watchdog.log"
$MaxRestarts = 25
$HealthFailureThreshold = 4
Set-Location $RepoRoot
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null

function Write-JsonUtf8 {
    param(
        [Parameter(Mandatory = $true)] [string] $Path,
        [Parameter(Mandatory = $true)] $Value
    )
    $Encoding = [System.Text.UTF8Encoding]::new($false)
    $Json = $Value | ConvertTo-Json -Depth 20
    [System.IO.File]::WriteAllText($Path, $Json, $Encoding)
}

function Write-WatchdogEvent {
    param(
        [Parameter(Mandatory = $true)] [string] $Message
    )
    $Line = (Get-Date).ToUniversalTime().ToString("o") + " " + $Message
    Add-Content -Path $WatchdogLog -Encoding UTF8 -Value $Line
    Write-Host $Message -ForegroundColor Yellow
}

function Test-MonitorHealth {
    try {
        $Response = Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 2
        return $Response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

function Show-LogTail {
    param(
        [string] $Path,
        [string] $Label
    )
    if (-not (Test-Path $Path)) { return }
    $Lines = @(Get-Content -Path $Path -Tail 20 -ErrorAction SilentlyContinue)
    if ($Lines.Count -eq 0) { return }
    Write-Host ""
    Write-Host $Label -ForegroundColor Red
    $Lines | ForEach-Object { Write-Host $_ -ForegroundColor DarkYellow }
}

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
Write-Host "NEXORA - Supervisor del Monitor por Capas" -ForegroundColor Cyan
Write-Host "Repositorio: $RepoRoot"
Write-Host "El monitor se reiniciara automaticamente si Bun termina o pierde salud." -ForegroundColor Yellow
Write-Host "Todos los errores quedaran guardados en .nexora-monitor." -ForegroundColor Yellow
Write-Host ""

$Attempt = 0
$BrowserOpened = $false
$MonitorProcess = $null

try {
    while ($Attempt -lt $MaxRestarts) {
        $Attempt += 1
        $Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
        $StdoutLog = Join-Path $RuntimeDir ("monitor-stdout-" + $Stamp + "-a" + $Attempt + ".log")
        $StderrLog = Join-Path $RuntimeDir ("monitor-stderr-" + $Stamp + "-a" + $Attempt + ".log")

        Write-WatchdogEvent -Message ("Iniciando servidor Bun. Intento " + $Attempt + " de " + $MaxRestarts + ".")

        $MonitorProcess = Start-Process `
            -FilePath $Bun.Source `
            -ArgumentList "`"$Server`"" `
            -PassThru `
            -NoNewWindow `
            -RedirectStandardOutput $StdoutLog `
            -RedirectStandardError $StderrLog

        $Supervisor = [ordered]@{
            schema_version = 1
            status = "starting"
            attempt = $Attempt
            max_restarts = $MaxRestarts
            pid = $MonitorProcess.Id
            panel_url = $PanelUrl
            started_at = (Get-Date).ToUniversalTime().ToString("o")
            last_health_at = $null
            restart_reason = $null
            stdout_log = $StdoutLog
            stderr_log = $StderrLog
        }
        Write-JsonUtf8 -Path $SupervisorPath -Value $Supervisor

        $Ready = $false
        for ($Probe = 1; $Probe -le 40; $Probe++) {
            if ($MonitorProcess.HasExited) { break }
            if (Test-MonitorHealth) {
                $Ready = $true
                break
            }
            Start-Sleep -Milliseconds 500
        }

        if (-not $Ready) {
            $Reason = if ($MonitorProcess.HasExited) {
                "Bun termino antes de responder al health check."
            }
            else {
                "El health check no respondio despues de 20 segundos."
            }

            if (-not $MonitorProcess.HasExited) {
                Stop-Process -Id $MonitorProcess.Id -Force -ErrorAction SilentlyContinue
                Start-Sleep -Milliseconds 500
            }

            $Supervisor.status = "restarting"
            $Supervisor.restart_reason = $Reason
            Write-JsonUtf8 -Path $SupervisorPath -Value $Supervisor
            Write-WatchdogEvent -Message $Reason
            Show-LogTail -Path $StderrLog -Label "Ultimas lineas de stderr:"
            Show-LogTail -Path $StdoutLog -Label "Ultimas lineas de stdout:"
            Start-Sleep -Seconds ([Math]::Min(15, 2 + $Attempt))
            continue
        }

        $Supervisor.status = "healthy"
        $Supervisor.last_health_at = (Get-Date).ToUniversalTime().ToString("o")
        Write-JsonUtf8 -Path $SupervisorPath -Value $Supervisor

        Write-Host "Monitor activo: $PanelUrl" -ForegroundColor Green
        Write-Host ("PID Bun: " + $MonitorProcess.Id) -ForegroundColor Cyan
        Write-Host "Auditoria y certificacion se calculan por separado." -ForegroundColor Cyan

        if (-not $BrowserOpened) {
            Start-Process $PanelUrl
            $BrowserOpened = $true
        }

        $ConsecutiveFailures = 0
        $RestartReason = ""

        while (-not $MonitorProcess.HasExited) {
            Start-Sleep -Seconds 3

            if (Test-MonitorHealth) {
                $ConsecutiveFailures = 0
                $Supervisor.status = "healthy"
                $Supervisor.last_health_at = (Get-Date).ToUniversalTime().ToString("o")
                Write-JsonUtf8 -Path $SupervisorPath -Value $Supervisor
                continue
            }

            $ConsecutiveFailures += 1
            Write-WatchdogEvent -Message ("Health check fallido " + $ConsecutiveFailures + " de " + $HealthFailureThreshold + ".")

            if ($ConsecutiveFailures -ge $HealthFailureThreshold) {
                $RestartReason = "El servidor dejo de responder durante " + $HealthFailureThreshold + " comprobaciones consecutivas."
                Stop-Process -Id $MonitorProcess.Id -Force -ErrorAction SilentlyContinue
                break
            }
        }

        $MonitorProcess.Refresh()
        if ([string]::IsNullOrWhiteSpace($RestartReason)) {
            $RestartReason = "El proceso Bun termino con codigo " + $MonitorProcess.ExitCode + "."
        }

        $Supervisor.status = "restarting"
        $Supervisor.restart_reason = $RestartReason
        Write-JsonUtf8 -Path $SupervisorPath -Value $Supervisor
        Write-WatchdogEvent -Message $RestartReason
        Show-LogTail -Path $StderrLog -Label "Ultimas lineas de stderr:"
        Show-LogTail -Path $StdoutLog -Label "Ultimas lineas de stdout:"

        Start-Sleep -Seconds ([Math]::Min(20, 3 + $Attempt))
    }

    $FinalState = [ordered]@{
        schema_version = 1
        status = "failed"
        attempt = $Attempt
        max_restarts = $MaxRestarts
        panel_url = $PanelUrl
        finished_at = (Get-Date).ToUniversalTime().ToString("o")
        reason = "Se alcanzo el limite de reinicios automaticos."
        watchdog_log = $WatchdogLog
    }
    Write-JsonUtf8 -Path $SupervisorPath -Value $FinalState
    throw "El monitor alcanzo el limite de $MaxRestarts reinicios. Revise $WatchdogLog"
}
finally {
    if ($MonitorProcess -and -not $MonitorProcess.HasExited) {
        Stop-Process -Id $MonitorProcess.Id -Force -ErrorAction SilentlyContinue
    }
}
