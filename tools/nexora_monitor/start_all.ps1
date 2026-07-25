$ErrorActionPreference = "Stop"

[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [System.Text.UTF8Encoding]::new()
try { chcp 65001 | Out-Null } catch {}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
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

# LIVE_PROGRESS.json es estado transitorio del monitor, no código de producto.
# Se restaura antes de actualizar y se marca skip-worktree durante la sesión
# para que sus actualizaciones en vivo no bloqueen pull, commits ni reinicios.
$LiveProgressRelative = "docs/nexora/LIVE_PROGRESS.json"
$LiveProgressPath = Join-Path $RepoRoot $LiveProgressRelative
if (Test-Path $LiveProgressPath) {
    git update-index --no-skip-worktree -- $LiveProgressRelative 2>$null
    git restore --source=HEAD --worktree -- $LiveProgressRelative
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo restaurar el estado temporal del monitor."
    }
}

$Dirty = @(git status --porcelain | Where-Object {
    $_ -and ($_ -notmatch "docs/nexora/LIVE_PROGRESS\.json$")
})
if ($Dirty.Count -gt 0) {
    Write-Host "Hay cambios reales de código sin guardar. No se hará pull ni se iniciará otra ejecución." -ForegroundColor Red
    $Dirty | ForEach-Object { Write-Host $_ }
    throw "Revisa únicamente los cambios mostrados antes de continuar."
}

Write-Host "Actualizando nexora-continuidad-total mediante fast-forward..." -ForegroundColor Cyan
git pull --ff-only origin nexora-continuidad-total
if ($LASTEXITCODE -ne 0) {
    throw "git pull falló. No se inició OpenCode."
}

if (Test-Path $LiveProgressPath) {
    git update-index --skip-worktree -- $LiveProgressRelative
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo preparar LIVE_PROGRESS.json para la sesión en vivo."
    }
}

$RuntimeDir = Join-Path $RepoRoot ".nexora-monitor"
$LogPath = Join-Path $RuntimeDir "opencode-live.log"
$SessionPath = Join-Path $RuntimeDir "session.json"
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null
[System.IO.File]::WriteAllText($LogPath, "", [System.Text.UTF8Encoding]::new($false))

$Session = [ordered]@{
    status = "running"
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
Start-Sleep -Seconds 3

$OpenCode = Get-Command opencode -ErrorAction SilentlyContinue
if (-not $OpenCode) {
    $Session.status = "failed"
    $Session.finished_at = (Get-Date).ToUniversalTime().ToString("o")
    $Session.exit_code = 127
    Write-JsonUtf8 -Path $SessionPath -Value $Session
    throw "OpenCode no está disponible en PATH. Comprueba con: opencode --version"
}

$Prompt = @"
Lee y obedece AGENTS.md, docs/nexora/ORDEN_MAESTRA_FINALIZACION.md, docs/nexora/AUDITORIA_CORRECCION_FINAL.md y docs/nexora/PROTOCOLO_REVISION_Y_FUSION.md. Continúa automáticamente la corrección final punto por punto sobre la rama nexora-continuidad-total y el PR #12. Usa el código, la matriz oficial de 166 requisitos, los logs remotos y los workflows como fuente de verdad. Actualiza docs/nexora/LIVE_PROGRESS.json antes y después de cada prueba y corrección importante; es estado local transitorio del monitor y no debe incluirse en commits. Corrige causas raíz, ejecuta pruebas positivas y negativas, permisos, idempotencia, concurrencia, rollback, instalación, migración, uninstall/reinstall, seed doble, pre-commit dos veces, Semgrep y GitHub Actions. Haz commits semánticos y push únicamente a origin/nexora-continuidad-total. No preguntes si debes continuar al siguiente punto. No fusiones, no crees tags, no despliegues, no toques main, producción, AWS, Coolify ni DNS. No declares terminado mientras no existan 166/166 requisitos con evidencia individual y todos los controles obligatorios verdes sobre el mismo SHA completo. Cuando todo esté realmente cumplido, crea docs/nexora/FINAL_REVIEW_PACKAGE.md con la evidencia completa, haz el último commit y push, comprueba HEAD remoto y árbol limpio ignorando únicamente LIVE_PROGRESS.json, actualiza LIVE_PROGRESS.json con agent_status awaiting_review y deja como última instrucción exacta: Regrese a ChatGPT y escriba: Revisa el paquete final de NEXORA y el HEAD actual del PR #12. Después detente sin fusionar. OpenCode no puede invocar esta conversación de ChatGPT automáticamente. Detente antes solo ante un bloqueo real o una acción expresamente prohibida.
"@

Write-Host ""
Write-Host "Monitor abierto en http://127.0.0.1:8765" -ForegroundColor Green
Write-Host "Iniciando OpenCode con captura automática de consola..." -ForegroundColor Green
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
Write-Host "OpenCode terminó o se detuvo con código $ExitCode. El monitor permanece abierto." -ForegroundColor Yellow
