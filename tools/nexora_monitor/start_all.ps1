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
    $Json = $Value | ConvertTo-Json -Depth 40
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

function Test-PowerShellFile {
    param([Parameter(Mandatory = $true)] [string] $Path)
    $ParserTokens = $null
    $ParserErrors = $null
    [System.Management.Automation.Language.Parser]::ParseFile(
        $Path,
        [ref] $ParserTokens,
        [ref] $ParserErrors
    ) | Out-Null

    if ($ParserErrors.Count -gt 0) {
        Write-Host "Errores de sintaxis en $Path" -ForegroundColor Red
        $ParserErrors | ForEach-Object {
            Write-Host ("Linea " + $_.Extent.StartLineNumber + ": " + $_.Message) -ForegroundColor Red
        }
        throw "La ejecucion se detuvo antes de abrir ventanas."
    }
}

$Branch = (git branch --show-current).Trim()
if ($Branch -ne "nexora-continuidad-total") {
    throw "Rama incorrecta: $Branch. Debe ser nexora-continuidad-total."
}

$RuntimeDir = Join-Path $RepoRoot ".nexora-monitor"
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null

$LiveProgressRelative = "docs/nexora/LIVE_PROGRESS.json"
if (Test-Path (Join-Path $RepoRoot $LiveProgressRelative)) {
    git update-index --no-skip-worktree -- $LiveProgressRelative 2>$null
}

$DirtyLines = @(git status --porcelain)
$PreservedChanges = @()
foreach ($Line in $DirtyLines) {
    if (-not $Line) { continue }
    $Path = Get-PorcelainPath -Line $Line
    if ([string]::IsNullOrWhiteSpace($Path)) { continue }
    $PreservedChanges += [pscustomobject]@{
        Line = $Line
        Path = $Path
        Exists = Test-Path -LiteralPath (Join-Path $RepoRoot $Path)
    }
}

$RecoveryDir = ""
if ($PreservedChanges.Count -gt 0) {
    $Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $RecoveryDir = Join-Path $RuntimeDir ("recovery\" + $Timestamp)
    $WorktreeBackup = Join-Path $RecoveryDir "worktree"
    New-Item -ItemType Directory -Force -Path $WorktreeBackup | Out-Null

    $PreservedFiles = @()
    foreach ($Change in $PreservedChanges) {
        $Source = Join-Path $RepoRoot $Change.Path
        $Hash = $null
        if (Test-Path -LiteralPath $Source) {
            $Destination = Join-Path $WorktreeBackup $Change.Path
            $DestinationParent = Split-Path $Destination -Parent
            New-Item -ItemType Directory -Force -Path $DestinationParent | Out-Null
            Copy-Item -LiteralPath $Source -Destination $Destination -Force
            $Hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Source).Hash
        }
        $PreservedFiles += [pscustomobject]@{
            path = $Change.Path
            status = $Change.Line.Substring(0, 2)
            existed = $Change.Exists
            sha256 = $Hash
        }
    }

    git diff --binary |
        Set-Content -Path (Join-Path $RecoveryDir "working-tree.patch") -Encoding UTF8
    git diff --cached --binary |
        Set-Content -Path (Join-Path $RecoveryDir "index.patch") -Encoding UTF8
    git status --short |
        Set-Content -Path (Join-Path $RecoveryDir "git-status.txt") -Encoding UTF8

    $Manifest = [ordered]@{
        schema_version = 2
        created_at = (Get-Date).ToUniversalTime().ToString("o")
        local_head = (git rev-parse HEAD).Trim()
        branch = $Branch
        files = $PreservedFiles
        status_lines = @($PreservedChanges | ForEach-Object { $_.Line })
        working_tree_patch = "working-tree.patch"
        index_patch = "index.patch"
    }
    Write-JsonUtf8 -Path (Join-Path $RecoveryDir "manifest.json") -Value $Manifest

    [System.IO.File]::WriteAllText(
        (Join-Path $RuntimeDir "latest-recovery.txt"),
        $RecoveryDir,
        [System.Text.UTF8Encoding]::new($false)
    )

    Write-Host "Todos los cambios locales fueron preservados:" -ForegroundColor Yellow
    $PreservedChanges | ForEach-Object { Write-Host ("  " + $_.Line) }
    Write-Host "Copia verificable: $RecoveryDir" -ForegroundColor Cyan
}

Write-Host "Consultando el HEAD remoto autorizado..." -ForegroundColor Cyan
git fetch origin nexora-continuidad-total
if ($LASTEXITCODE -ne 0) {
    throw "git fetch fallo. Las copias de recuperacion permanecen guardadas."
}

$RemoteHead = (git rev-parse origin/nexora-continuidad-total).Trim()
$LocalHead = (git rev-parse HEAD).Trim()
git merge-base --is-ancestor $LocalHead $RemoteHead
if ($LASTEXITCODE -ne 0) {
    throw "La rama local no puede actualizarse mediante fast-forward. No se realizo merge, rebase ni reset."
}

$RemoteChangedPaths = @()
if ($LocalHead -ne $RemoteHead) {
    $RemoteChangedPaths = @(git diff --name-only ($LocalHead + ".." + $RemoteHead))
}

$OverlapPaths = @(
    $PreservedChanges |
    Where-Object { $RemoteChangedPaths -contains $_.Path }
)

if ($OverlapPaths.Count -gt 0) {
    Write-Host "El remoto tambien modifico algunos archivos locales preservados:" -ForegroundColor Yellow
    foreach ($Overlap in $OverlapPaths) {
        Write-Host ("  " + $Overlap.Path) -ForegroundColor Yellow
        git ls-files --error-unmatch -- $Overlap.Path 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            git restore --source=HEAD --staged --worktree -- $Overlap.Path
            if ($LASTEXITCODE -ne 0) {
                throw "No se pudo apartar de forma segura $($Overlap.Path). La copia permanece en $RecoveryDir"
            }
        }
        elseif (Test-Path -LiteralPath (Join-Path $RepoRoot $Overlap.Path)) {
            Remove-Item -LiteralPath (Join-Path $RepoRoot $Overlap.Path) -Force
        }
    }
    Write-Host "Las versiones locales completas siguen en la carpeta de recuperacion." -ForegroundColor Cyan
}

Write-Host "Actualizando nexora-continuidad-total mediante fast-forward..." -ForegroundColor Cyan
git pull --ff-only origin nexora-continuidad-total
if ($LASTEXITCODE -ne 0) {
    throw "git pull fallo. No se inicio OpenCode y las copias permanecen guardadas."
}

if (Test-Path (Join-Path $RepoRoot $LiveProgressRelative)) {
    git update-index --skip-worktree -- $LiveProgressRelative 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo preparar LIVE_PROGRESS.json para la sesion."
    }
}

$MonitorScript = Join-Path $PSScriptRoot "start_monitor.ps1"
$RunnerScript = Join-Path $PSScriptRoot "run_opencode.ps1"
$FinalAuthorization = Join-Path $PSScriptRoot "final_authorization.ps1"
$SelfCheck = Join-Path $PSScriptRoot "monitor_selfcheck.js"
$RequiredFiles = @($MonitorScript, $RunnerScript, $FinalAuthorization, $SelfCheck)
foreach ($RequiredFile in $RequiredFiles) {
    if (-not (Test-Path $RequiredFile)) {
        throw "Falta un archivo obligatorio: $RequiredFile"
    }
}

Test-PowerShellFile -Path $MonitorScript
Test-PowerShellFile -Path $RunnerScript
Test-PowerShellFile -Path $FinalAuthorization
Write-Host "Sintaxis PowerShell verificada." -ForegroundColor Green

$Bun = Get-Command bun -ErrorAction SilentlyContinue
if (-not $Bun) {
    throw "Bun no esta disponible. Compruebe con: bun --version"
}

& bun $SelfCheck
if ($LASTEXITCODE -ne 0) {
    throw "La autoprueba del monitor fallo. No se abriran ventanas."
}
Write-Host "Autoprueba del monitor aprobada." -ForegroundColor Green

$ExistingListeners = @(Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue)
foreach ($Listener in $ExistingListeners) {
    Write-Host ("Cerrando monitor anterior PID " + $Listener.OwningProcess) -ForegroundColor Yellow
    Stop-Process -Id $Listener.OwningProcess -Force -ErrorAction SilentlyContinue
}
if ($ExistingListeners.Count -gt 0) {
    Start-Sleep -Seconds 1
}

$SessionPath = Join-Path $RuntimeDir "session.json"
$Session = [ordered]@{
    schema_version = 2
    status = "starting"
    started_at = (Get-Date).ToUniversalTime().ToString("o")
    finished_at = $null
    exit_code = $null
    branch = "nexora-continuidad-total"
    pull_request = 12
    head = (git rev-parse HEAD).Trim()
    mode = "OpenCode bounded layered audit sessions"
    active_block = $null
    preserved_changes = @($PreservedChanges | ForEach-Object { $_.Path })
    recovery_dir = $RecoveryDir
}
Write-JsonUtf8 -Path $SessionPath -Value $Session
$env:NEXORA_RECOVERY_DIR = $RecoveryDir

$MonitorArgs = "-NoExit -NoProfile -ExecutionPolicy Bypass -File `"$MonitorScript`""
Start-Process powershell.exe -ArgumentList $MonitorArgs

$MonitorReady = $false
for ($Attempt = 1; $Attempt -le 50; $Attempt++) {
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
    throw "El supervisor del monitor no inicio correctamente. Revise la ventana azul."
}

$OpenCode = Get-Command opencode -ErrorAction SilentlyContinue
if (-not $OpenCode) {
    throw "OpenCode no esta disponible. Compruebe con: opencode --version"
}

Write-Host ""
Write-Host "Monitor autorrecuperable confirmado en $PanelUrl" -ForegroundColor Green
Write-Host "Abriendo OpenCode en sesiones acotadas y reanudables..." -ForegroundColor Green
Write-Host "La auditoria continuara desde el primer resultado no final." -ForegroundColor Cyan
Write-Host ""

$RunnerArgs = "-NoExit -NoProfile -ExecutionPolicy Bypass -File `"$RunnerScript`""
$RunnerProcess = Start-Process powershell.exe -ArgumentList $RunnerArgs -PassThru

Write-Host "OpenCode esta ejecutandose en la nueva ventana." -ForegroundColor Green
Write-Host "Mantenga abiertas la ventana azul, OpenCode y el navegador." -ForegroundColor Yellow
Wait-Process -Id $RunnerProcess.Id
$RunnerProcess.Refresh()

Write-Host ""
Write-Host "La ventana de OpenCode se cerro. El supervisor del monitor sigue abierto en $PanelUrl" -ForegroundColor Yellow
Write-Host "La fusion permanece bloqueada hasta la puerta final y otra autorizacion expresa." -ForegroundColor Red
