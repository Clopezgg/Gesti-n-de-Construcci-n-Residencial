$ErrorActionPreference = "Stop"

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
    $Json = $Value | ConvertTo-Json -Depth 10
    [System.IO.File]::WriteAllText($Path, $Json, $Encoding)
}

$Branch = (git branch --show-current).Trim()
if ($Branch -ne "nexora-continuidad-total") {
    throw "Rama incorrecta: $Branch. Debe ser nexora-continuidad-total."
}

# LIVE_PROGRESS.json contiene estado local temporal del monitor.
# Se restaura antes del pull y se excluye del seguimiento durante la sesion.
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
$LogPath = Join-Path $RuntimeDir "opencode-live.log"
$SessionPath = Join-Path $RuntimeDir "session.json"
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null
[System.IO.File]::WriteAllText($LogPath, "", [System.Text.UTF8Encoding]::new($false))

$Session = [ordered]@{
    status = "starting"
    started_at = (Get-Date).ToUniversalTime().ToString("o")
    finished_at = $null
    exit_code = $null
    branch = "nexora-continuidad-total"
    pull_request = 12
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
    throw "El monitor no inicio correctamente. Revise la otra ventana de PowerShell."
}

$OpenCode = Get-Command opencode -ErrorAction SilentlyContinue
if (-not $OpenCode) {
    $Session.status = "failed"
    $Session.finished_at = (Get-Date).ToUniversalTime().ToString("o")
    $Session.exit_code = 127
    Write-JsonUtf8 -Path $SessionPath -Value $Session
    throw "OpenCode no esta disponible. Compruebe con: opencode --version"
}

$Session.status = "running"
Write-JsonUtf8 -Path $SessionPath -Value $Session

$Prompt = @"
Lee y obedece AGENTS.md, docs/nexora/ORDEN_MAESTRA_FINALIZACION.md, docs/nexora/AUDITORIA_CORRECCION_FINAL.md y docs/nexora/PROTOCOLO_REVISION_Y_FUSION.md. Continua automaticamente la correccion final punto por punto sobre la rama nexora-continuidad-total y el PR #12. Usa el codigo, la matriz oficial de 166 requisitos, los logs remotos y los workflows como fuente de verdad. Actualiza docs/nexora/LIVE_PROGRESS.json antes y despues de cada prueba y correccion importante; es estado local transitorio y no debe incluirse en commits. Corrige causas raiz, ejecuta pruebas positivas y negativas, permisos, idempotencia, concurrencia, rollback, instalacion, migracion, uninstall/reinstall, seed doble, pre-commit dos veces, Semgrep y GitHub Actions. Haz commits semanticos y push unicamente a origin/nexora-continuidad-total. No preguntes si debes continuar. No fusiones, no crees tags, no despliegues y no toques main, produccion, AWS, Coolify ni DNS. No declares terminado mientras no existan 166/166 requisitos con evidencia individual y todos los controles obligatorios verdes sobre el mismo SHA completo. Cuando todo este realmente cumplido, crea docs/nexora/FINAL_REVIEW_PACKAGE.md con la evidencia completa, haz el ultimo commit y push, comprueba HEAD remoto y arbol limpio ignorando unicamente LIVE_PROGRESS.json, actualiza LIVE_PROGRESS.json con agent_status awaiting_review y deja como ultima instruccion exacta: Regrese a ChatGPT y escriba: Revisa el paquete final de NEXORA y el HEAD actual del PR #12. Despues detente sin fusionar. OpenCode no puede invocar esta conversacion de ChatGPT automaticamente. Detente antes solo ante un bloqueo real o una accion expresamente prohibida.
"@

Write-Host ""
Write-Host "Monitor confirmado en $PanelUrl" -ForegroundColor Green
Write-Host "Iniciando OpenCode con captura automatica de consola..." -ForegroundColor Green
Write-Host ""

$Encoding = [System.Text.UTF8Encoding]::new($false)
$Writer = [System.IO.StreamWriter]::new($LogPath, $false, $Encoding)
$ExitCode = 1
try {
    & opencode run $Prompt 2>&1 | ForEach-Object {
        $Line = ($_ | Out-String).TrimEnd()
        if ($Line) {
            $Writer.WriteLine($Line)
            $Writer.Flush()
            Write-Host $Line
        }
    }
    $ExitCode = $LASTEXITCODE
}
finally {
    $Writer.Flush()
    $Writer.Dispose()
    $Session.status = if ($ExitCode -eq 0) { "finished" } else { "failed" }
    $Session.finished_at = (Get-Date).ToUniversalTime().ToString("o")
    $Session.exit_code = $ExitCode
    Write-JsonUtf8 -Path $SessionPath -Value $Session
}

Write-Host ""
Write-Host "OpenCode termino o se detuvo con codigo $ExitCode. El monitor permanece abierto." -ForegroundColor Yellow
