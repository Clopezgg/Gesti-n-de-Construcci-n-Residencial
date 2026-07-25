$ErrorActionPreference = "Stop"

[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [System.Text.UTF8Encoding]::new()
try { chcp 65001 | Out-Null } catch {}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$RuntimeDir = Join-Path $RepoRoot ".nexora-monitor"
$SessionPath = Join-Path $RuntimeDir "session.json"
$LogPath = Join-Path $RuntimeDir "opencode-live.log"
$LivePath = Join-Path $RepoRoot "docs\nexora\LIVE_PROGRESS.json"
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

function Update-LiveProgress {
    param(
        [string] $AgentStatus,
        [string] $Phase,
        [string] $Task,
        [string] $Detail
    )

    if (-not (Test-Path $LivePath)) { return }

    try {
        $Live = Get-Content -Raw -Path $LivePath | ConvertFrom-Json
        $Live.agent_status = $AgentStatus
        $Live.phase = $Phase
        $Live.task = $Task
        $Live.detail = $Detail
        $Live.last_update = (Get-Date).ToUniversalTime().ToString("o")
        Write-JsonUtf8 -Path $LivePath -Value $Live
    }
    catch {
        Add-Content -Path $LogPath -Encoding UTF8 -Value "No se pudo actualizar LIVE_PROGRESS.json: $($_.Exception.Message)"
    }
}

$OpenCode = Get-Command opencode -ErrorAction SilentlyContinue
if (-not $OpenCode) {
    throw "OpenCode no esta disponible. Compruebe con: opencode --version"
}

$Prompt = @"
Lee y obedece completamente AGENTS.md, docs/nexora/ORDEN_MAESTRA_FINALIZACION.md, docs/nexora/AUDITORIA_CORRECCION_FINAL.md y docs/nexora/PROTOCOLO_REVISION_Y_FUSION.md.

Trabaja directamente en nexora-continuidad-total y PR #12. Continua automaticamente punto por punto. Antes y despues de cada analisis, correccion, prueba, commit, push y consulta de GitHub Actions actualiza docs/nexora/LIVE_PROGRESS.json con la tarea exacta, detalle, bloque, prueba y resultado para alimentar el mapa visual en tiempo real.

Corrige causas raiz. Ejecuta pruebas positivas y negativas, permisos, idempotencia, concurrencia, rollback, instalacion, migracion, uninstall/reinstall, seed doble, pre-commit dos veces, Semgrep y GitHub Actions. Haz commits semanticos y push unicamente a origin/nexora-continuidad-total.

No preguntes si debes continuar. No fusiones, no crees tags, no despliegues y no toques main, produccion, AWS, Coolify ni DNS. No declares terminado hasta tener 166/166 requisitos con evidencia individual y todos los controles obligatorios verdes sobre el mismo SHA.

Cuando todo este realmente cumplido, crea docs/nexora/FINAL_REVIEW_PACKAGE.md, realiza el ultimo commit y push, comprueba HEAD remoto y arbol limpio ignorando solo LIVE_PROGRESS.json, marca agent_status como awaiting_review y muestra exactamente: Regrese a ChatGPT y escriba: Revisa el paquete final de NEXORA y el HEAD actual del PR #12. Luego detente sin fusionar.
"@

$Session = [ordered]@{
    status = "running"
    started_at = (Get-Date).ToUniversalTime().ToString("o")
    finished_at = $null
    exit_code = $null
    branch = "nexora-continuidad-total"
    pull_request = 12
    mode = "OpenCode TUI"
}
Write-JsonUtf8 -Path $SessionPath -Value $Session
[System.IO.File]::WriteAllText($LogPath, "OpenCode TUI iniciado: $((Get-Date).ToString('s'))`r`n", [System.Text.UTF8Encoding]::new($false))
Update-LiveProgress `
    -AgentStatus "working" `
    -Phase "Inicializacion automatica" `
    -Task "OpenCode esta leyendo las ordenes y preparando la auditoria" `
    -Detail "La ventana OpenCode TUI esta activa. El mapa visual se actualizara con LIVE_PROGRESS.json."

Write-Host ""
Write-Host "NEXORA - OpenCode Executor" -ForegroundColor Cyan
Write-Host "Rama: nexora-continuidad-total" -ForegroundColor Green
Write-Host "PR: #12" -ForegroundColor Green
Write-Host "El navegador muestra el mapa de correcciones en tiempo real." -ForegroundColor Yellow
Write-Host "No cierre esta ventana mientras OpenCode trabaja." -ForegroundColor Yellow
Write-Host ""

$ExitCode = 1
try {
    & opencode --auto --prompt $Prompt
    $ExitCode = $LASTEXITCODE
}
finally {
    $Session.status = if ($ExitCode -eq 0) { "finished" } else { "failed" }
    $Session.finished_at = (Get-Date).ToUniversalTime().ToString("o")
    $Session.exit_code = $ExitCode
    Write-JsonUtf8 -Path $SessionPath -Value $Session

    try {
        $Live = Get-Content -Raw -Path $LivePath | ConvertFrom-Json
        if ($Live.agent_status -ne "awaiting_review") {
            $Live.agent_status = if ($ExitCode -eq 0) { "finished" } else { "blocked" }
            $Live.phase = if ($ExitCode -eq 0) { "Ejecucion detenida" } else { "Bloqueo de ejecucion" }
            $Live.task = if ($ExitCode -eq 0) { "OpenCode termino la sesion" } else { "OpenCode termino con error" }
            $Live.detail = "Codigo de salida: $ExitCode"
            $Live.last_update = (Get-Date).ToUniversalTime().ToString("o")
            Write-JsonUtf8 -Path $LivePath -Value $Live
        }
    }
    catch {}

    Add-Content -Path $LogPath -Encoding UTF8 -Value "OpenCode termino con codigo $ExitCode: $((Get-Date).ToString('s'))"
}

Write-Host ""
Write-Host "OpenCode termino con codigo $ExitCode." -ForegroundColor Yellow
Write-Host "El monitor permanece disponible en http://127.0.0.1:8765" -ForegroundColor Cyan
