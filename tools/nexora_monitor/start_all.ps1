$ErrorActionPreference = "Stop"

[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [System.Text.UTF8Encoding]::new()
try { chcp 65001 | Out-Null } catch {}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$PanelUrl = "http://127.0.0.1:8765"
$HealthUrl = "$PanelUrl/health"
Set-Location $RepoRoot

function Write-JsonUtf8 {
    param(
        [Parameter(Mandatory = $true)] [string] $Path,
        [Parameter(Mandatory = $true)] $Value
    )
    $Encoding = [System.Text.UTF8Encoding]::new($false)
    $Json = $Value | ConvertTo-Json -Depth 20
    [System.IO.File]::WriteAllText($Path, $Json, $Encoding)
}

function Get-PorcelainPath {
    param([Parameter(Mandatory = $true)] [string] $Line)
    if ($Line.Length -lt 4) { return "" }
    $Path = $Line.Substring(3).Trim()
    if ($Path -match " -> ") {
        $Path = ($Path -split " -> ")[-1].Trim()
    }
    return $Path.Trim('"')
}

$Branch = (git branch --show-current).Trim()
if ($Branch -ne "nexora-continuidad-total") {
    throw "Rama incorrecta: $Branch. Debe ser nexora-continuidad-total."
}

$AllowedRecoveryPaths = @(
    "EXECUTION_STATE.md",
    "docs/nexora/MATRIZ_REQUISITOS.md",
    "docs/nexora/CHECKPOINT.md",
    "docs/nexora/LIVE_PROGRESS.json"
)

$DirtyLines = @(git status --porcelain)
$PreservedChanges = @()
$UnexpectedChanges = @()

foreach ($Line in $DirtyLines) {
    if (-not $Line) { continue }
    $Path = Get-PorcelainPath -Line $Line
    if ($AllowedRecoveryPaths -contains $Path) {
        $PreservedChanges += [pscustomobject]@{ Line = $Line; Path = $Path }
    }
    else {
        $UnexpectedChanges += $Line
    }
}

if ($UnexpectedChanges.Count -gt 0) {
    Write-Host "Hay cambios inesperados de codigo sin guardar:" -ForegroundColor Red
    $UnexpectedChanges | ForEach-Object { Write-Host $_ }
    throw "El inicio se detuvo para no perder cambios de codigo."
}

$RuntimeDir = Join-Path $RepoRoot ".nexora-monitor"
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null

if ($PreservedChanges.Count -gt 0) {
    $Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $RecoveryDir = Join-Path $RuntimeDir ("recovery\" + $Timestamp)
    New-Item -ItemType Directory -Force -Path $RecoveryDir | Out-Null

    foreach ($Change in $PreservedChanges) {
        $Source = Join-Path $RepoRoot $Change.Path
        if (Test-Path $Source) {
            $Destination = Join-Path $RecoveryDir $Change.Path
            $DestinationParent = Split-Path $Destination -Parent
            New-Item -ItemType Directory -Force -Path $DestinationParent | Out-Null
            Copy-Item -Path $Source -Destination $Destination -Force
        }
    }

    Write-Host "Se detecto trabajo documental previo y fue preservado:" -ForegroundColor Yellow
    $PreservedChanges | ForEach-Object { Write-Host ("  " + $_.Line) }
    Write-Host "Copia de seguridad local: $RecoveryDir" -ForegroundColor Cyan
    Write-Host "OpenCode revisara, validara y decidira si debe corregir o incluir estos cambios." -ForegroundColor Yellow
}

Write-Host "Actualizando nexora-continuidad-total mediante fast-forward..." -ForegroundColor Cyan
git pull --ff-only origin nexora-continuidad-total
if ($LASTEXITCODE -ne 0) {
    throw "git pull fallo. Las copias de recuperacion permanecen guardadas."
}

$LiveProgressRelative = "docs/nexora/LIVE_PROGRESS.json"
$LiveProgressPath = Join-Path $RepoRoot $LiveProgressRelative
if (Test-Path $LiveProgressPath) {
    git update-index --skip-worktree -- $LiveProgressRelative 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo preparar LIVE_PROGRESS.json para la sesion."
    }
}

$SessionPath = Join-Path $RuntimeDir "session.json"
$Session = [ordered]@{
    status = "starting"
    started_at = (Get-Date).ToUniversalTime().ToString("o")
    finished_at = $null
    exit_code = $null
    branch = "nexora-continuidad-total"
    pull_request = 12
    mode = "OpenCode TUI"
    preserved_changes = @($PreservedChanges | ForEach-Object { $_.Path })
}
Write-JsonUtf8 -Path $SessionPath -Value $Session

$MonitorScript = Join-Path $PSScriptRoot "start_monitor.ps1"
$MonitorArgs = "-NoExit -ExecutionPolicy Bypass -File `"$MonitorScript`""
Start-Process powershell.exe -ArgumentList $MonitorArgs

$MonitorReady = $false
for ($Attempt = 1; $Attempt -le 40; $Attempt++) {
    try {
        $Response = Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 2
        if ($Response.StatusCode -eq 200) {
            $MonitorReady = $true
            break
        }
    }
    catch {
        Start-Sleep -Milliseconds 500
    }
}

if (-not $MonitorReady) {
    $Session.status = "failed"
    $Session.finished_at = (Get-Date).ToUniversalTime().ToString("o")
    $Session.exit_code = 125
    Write-JsonUtf8 -Path $SessionPath -Value $Session
    throw "El monitor no inicio correctamente. Revise la ventana azul."
}

$OpenCode = Get-Command opencode -ErrorAction SilentlyContinue
if (-not $OpenCode) {
    $Session.status = "failed"
    $Session.finished_at = (Get-Date).ToUniversalTime().ToString("o")
    $Session.exit_code = 127
    Write-JsonUtf8 -Path $SessionPath -Value $Session
    throw "OpenCode no esta disponible. Compruebe con: opencode --version"
}

$RunnerScript = Join-Path $PSScriptRoot "run_opencode.ps1"
if (-not (Test-Path $RunnerScript)) {
    throw "No se encontro el ejecutor de OpenCode: $RunnerScript"
}

Write-Host ""
Write-Host "Monitor confirmado en $PanelUrl" -ForegroundColor Green
Write-Host "Abriendo OpenCode en su propia ventana..." -ForegroundColor Green
Write-Host "El navegador mostrara lectura, analisis, prueba, diagnostico, correccion, repeticion, commit, push y CI." -ForegroundColor Cyan
Write-Host ""

$RunnerArgs = "-NoExit -ExecutionPolicy Bypass -File `"$RunnerScript`""
$RunnerProcess = Start-Process powershell.exe -ArgumentList $RunnerArgs -PassThru

Write-Host "OpenCode esta ejecutandose en la nueva ventana." -ForegroundColor Green
Write-Host "Mantenga abiertas la ventana azul, la ventana de OpenCode y el navegador." -ForegroundColor Yellow

Wait-Process -Id $RunnerProcess.Id
$RunnerProcess.Refresh()

Write-Host ""
Write-Host "La ventana de OpenCode se cerro. El monitor sigue abierto en $PanelUrl" -ForegroundColor Yellow
