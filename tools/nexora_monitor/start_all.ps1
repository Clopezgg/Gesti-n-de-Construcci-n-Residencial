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

$Branch = (git branch --show-current).Trim()
if ($Branch -ne "nexora-continuidad-total") {
    throw "Rama incorrecta: $Branch. Debe ser nexora-continuidad-total."
}

$LiveProgressRelative = "docs/nexora/LIVE_PROGRESS.json"
$LiveProgressPath = Join-Path $RepoRoot $LiveProgressRelative
if (Test-Path $LiveProgressPath) {
    git update-index --no-skip-worktree -- $LiveProgressRelative 2>$null
    git restore --source=HEAD --worktree -- $LiveProgressRelative
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo restaurar LIVE_PROGRESS.json."
    }
}

$Dirty = @(git status --porcelain | Where-Object {
    $_ -and ($_ -notmatch "docs/nexora/LIVE_PROGRESS\.json$")
})
if ($Dirty.Count -gt 0) {
    Write-Host "Hay cambios reales de codigo sin guardar:" -ForegroundColor Red
    $Dirty | ForEach-Object { Write-Host $_ }
    throw "Revise los cambios mostrados antes de continuar."
}

Write-Host "Actualizando nexora-continuidad-total..." -ForegroundColor Cyan
git pull --ff-only origin nexora-continuidad-total
if ($LASTEXITCODE -ne 0) {
    throw "git pull fallo. No se inicio OpenCode."
}

if (Test-Path $LiveProgressPath) {
    git update-index --skip-worktree -- $LiveProgressRelative
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo preparar LIVE_PROGRESS.json para la sesion."
    }
}

$RuntimeDir = Join-Path $RepoRoot ".nexora-monitor"
$SessionPath = Join-Path $RuntimeDir "session.json"
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null

$Session = [ordered]@{
    status = "starting"
    started_at = (Get-Date).ToUniversalTime().ToString("o")
    finished_at = $null
    exit_code = $null
    branch = "nexora-continuidad-total"
    pull_request = 12
    mode = "OpenCode TUI"
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
Write-Host "El navegador mostrara el mapa de analisis, fallo, correccion, nueva prueba, commit, push y CI." -ForegroundColor Cyan
Write-Host ""

$RunnerArgs = "-NoExit -ExecutionPolicy Bypass -File `"$RunnerScript`""
$RunnerProcess = Start-Process powershell.exe -ArgumentList $RunnerArgs -PassThru

Write-Host "OpenCode esta ejecutandose en la nueva ventana." -ForegroundColor Green
Write-Host "Mantenga abiertas la ventana azul, la ventana de OpenCode y el navegador." -ForegroundColor Yellow

Wait-Process -Id $RunnerProcess.Id
$RunnerProcess.Refresh()

Write-Host ""
Write-Host "La ventana de OpenCode se cerro. El monitor sigue abierto en $PanelUrl" -ForegroundColor Yellow
