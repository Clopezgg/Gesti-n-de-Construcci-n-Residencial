$ErrorActionPreference = "Stop"

[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [System.Text.UTF8Encoding]::new()
try { chcp 65001 | Out-Null } catch {}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$RuntimeDir = Join-Path $RepoRoot ".nexora-monitor"
$SessionPath = Join-Path $RuntimeDir "session.json"
$LogPath = Join-Path $RuntimeDir "opencode-live.log"
$LivePath = Join-Path $RepoRoot "docs\nexora\LIVE_PROGRESS.json"
$AuditCli = Join-Path $PSScriptRoot "audit_cli.js"
$AuditUpdate = Join-Path $PSScriptRoot "audit_update.js"
$AuditMandate = Join-Path $RepoRoot "docs\nexora\OPENCODE_AUDIT_MANDATE.md"
$FinalGateCheck = Join-Path $PSScriptRoot "final_gate_check.js"
$FinalAuthorization = Join-Path $PSScriptRoot "final_authorization.ps1"
Set-Location $RepoRoot
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null

function Write-JsonUtf8 {
    param(
        [Parameter(Mandatory = $true)] [string] $Path,
        [Parameter(Mandatory = $true)] $Value
    )
    $Encoding = [System.Text.UTF8Encoding]::new($false)
    $Json = $Value | ConvertTo-Json -Depth 30
    [System.IO.File]::WriteAllText($Path, $Json, $Encoding)
}

function Update-LiveProgress {
    param(
        [string] $AgentStatus,
        [string] $Phase,
        [Nullable[int]] $CurrentBlock,
        [string] $Task,
        [string] $Detail,
        [string] $BlockingIssue
    )

    if (-not (Test-Path $LivePath)) { return }

    try {
        $Live = Get-Content -Raw -Path $LivePath | ConvertFrom-Json
        $Live.agent_status = $AgentStatus
        $Live.phase = $Phase
        $Live.current_block = $CurrentBlock
        $Live.task = $Task
        $Live.detail = $Detail
        $Live.blocking_issue = if ([string]::IsNullOrWhiteSpace($BlockingIssue)) { $null } else { $BlockingIssue }
        $Live.last_update = (Get-Date).ToUniversalTime().ToString("o")
        Write-JsonUtf8 -Path $LivePath -Value $Live
    }
    catch {
        Add-Content -Path $LogPath -Encoding UTF8 -Value ("No se pudo actualizar LIVE_PROGRESS.json: " + $_.Exception.Message)
    }
}

$RequiredFiles = @($AuditCli, $AuditUpdate, $AuditMandate, $FinalGateCheck, $FinalAuthorization)
foreach ($RequiredFile in $RequiredFiles) {
    if (-not (Test-Path $RequiredFile)) {
        throw "No se encontro un componente obligatorio de auditoria: $RequiredFile"
    }
}

$AuthorizationTokens = $null
$AuthorizationErrors = $null
[System.Management.Automation.Language.Parser]::ParseFile(
    $FinalAuthorization,
    [ref] $AuthorizationTokens,
    [ref] $AuthorizationErrors
) | Out-Null
if ($AuthorizationErrors.Count -gt 0) {
    Write-Host "La ventana final contiene errores de sintaxis:" -ForegroundColor Red
    $AuthorizationErrors | ForEach-Object {
        Write-Host ("Linea " + $_.Extent.StartLineNumber + ": " + $_.Message) -ForegroundColor Red
    }
    throw "OpenCode no se abrira hasta corregir final_authorization.ps1."
}

$OpenCode = Get-Command opencode -ErrorAction SilentlyContinue
if (-not $OpenCode) {
    throw "OpenCode no esta disponible. Compruebe con: opencode --version"
}

$Bun = Get-Command bun -ErrorAction SilentlyContinue
if (-not $Bun) {
    throw "Bun no esta disponible. Compruebe con: bun --version"
}

$Branch = (git branch --show-current).Trim()
if ($Branch -ne "nexora-continuidad-total") {
    throw "Rama incorrecta: $Branch. Debe ser nexora-continuidad-total."
}

$Head = (git rev-parse HEAD).Trim()
if ($Head -notmatch "^[0-9a-f]{40}$") {
    throw "No se pudo obtener un HEAD completo valido."
}

Write-Host "Inicializando auditoria para HEAD $Head..." -ForegroundColor Cyan
& bun $AuditCli init $Head
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo inicializar AUDIT_RESULTS.json."
}

& bun $AuditCli validate
if ($LASTEXITCODE -ne 0) {
    throw "Los archivos canonicos de auditoria no son validos."
}

$Session = [ordered]@{
    status = "running"
    started_at = (Get-Date).ToUniversalTime().ToString("o")
    finished_at = $null
    exit_code = $null
    branch = "nexora-continuidad-total"
    pull_request = 12
    head = $Head
    mode = "OpenCode layered audit TUI"
    active_block = 0
    recovery_dir = $env:NEXORA_RECOVERY_DIR
}
Write-JsonUtf8 -Path $SessionPath -Value $Session
[System.IO.File]::WriteAllText(
    $LogPath,
    ("OpenCode auditoria por capas iniciada: " + (Get-Date).ToString("s") + "`r`nHEAD: " + $Head + "`r`n"),
    [System.Text.UTF8Encoding]::new($false)
)

Update-LiveProgress `
    -AgentStatus "working" `
    -Phase "Auditoria por capas - Bloque 0" `
    -CurrentBlock 0 `
    -Task "Reconstruyendo el objetivo original y auditando el Bloque 0" `
    -Detail ("HEAD " + $Head + ". La matriz documental no cuenta como certificacion real.") `
    -BlockingIssue ""

$Prompt = @'
La palabra SIRILAN autorizo esta auditoria y correccion completa.

Lee y obedece totalmente:
- AGENTS.md
- docs/nexora/ORDEN_MAESTRA_FINALIZACION.md
- docs/nexora/AUDITORIA_CORRECCION_FINAL.md
- docs/nexora/AUDITORIA_POR_CAPAS.md
- docs/nexora/OPENCODE_AUDIT_MANDATE.md
- docs/nexora/PROTOCOLO_REVISION_Y_FUSION.md
- docs/nexora/DEFECTS.json
- docs/nexora/AUDIT_RESULTS.json
- docs/nexora/MATRIZ_REQUISITOS.md
- EXECUTION_STATE.md

Empieza obligatoriamente por el Bloque 0 y avanza secuencialmente hasta el Bloque 20. No confies en que una fila de la matriz diga IMPLEMENTADO Y VALIDADO. Reconstruye el objetivo original, localiza implementacion real y ejecuta todas las validaciones que devuelve audit_cli.js.

Usa audit_update.js para actualizar resultados y defectos. No marques certified o not_applicable sin detalle, evidencia estructurada y SHA completo. Actualiza LIVE_PROGRESS.json antes y despues de cada requisito, diagnostico, correccion, prueba, commit, push y consulta de GitHub Actions.

Los ocho defectos iniciales de DEFECTS.json estan confirmados. Diagnostica sus causas desde jobs y logs completos. Los errores de linters deben agruparse por causa raiz; no silencies reglas ni reduzcas el alcance. Si un control global impide certificar el Bloque 0, corrigelo como dependencia del bloque activo, conservando su defecto en el bloque propietario.

Corrige causas raiz, ejecuta pruebas positivas y negativas, permisos server-side, idempotencia, integridad financiera, concurrencia, rollback, instalacion, migracion, uninstall/reinstall, seed doble, backup/restore, iPhone/PWA, pre-commit dos veces, Semgrep y GitHub Actions del mismo SHA cuando corresponda.

Haz commits semanticos y push unicamente a origin/nexora-continuidad-total. Nunca uses force push, reset --hard, clean -fd, continue-on-error, pruebas vacias o exclusiones artificiales.

No fusiones, no elimines ramas, no crees tags, no despliegues y no toques main, produccion, AWS, Coolify ni DNS. La puerta final solo puede activarse cuando audit_cli.js gate pase, todo CI obligatorio este verde sobre el mismo HEAD, el arbol este limpio y FINAL_REVIEW_PACKAGE.md diga APTO PARA REVISION con evidencia completa. Entonces marca awaiting_review y detente sin fusionar.
'@

if (-not [string]::IsNullOrWhiteSpace($env:NEXORA_RECOVERY_DIR)) {
    $Prompt += "`r`nExiste trabajo local preservado en: " + $env:NEXORA_RECOVERY_DIR + ". Lee manifest.json y compara cada copia con el HEAD actualizado. Recupera solo cambios validos, no sobrescribas a ciegas y registra la decision en LIVE_PROGRESS.json.`r`n"
}

Write-Host ""
Write-Host "NEXORA - OpenCode Auditor por Capas" -ForegroundColor Cyan
Write-Host "Rama: nexora-continuidad-total" -ForegroundColor Green
Write-Host "PR: #12" -ForegroundColor Green
Write-Host "HEAD: $Head" -ForegroundColor Green
Write-Host "Bloque inicial: 0" -ForegroundColor Yellow
Write-Host "El navegador mostrara cumple, no cumple objetivo y error tecnico." -ForegroundColor Yellow
if (-not [string]::IsNullOrWhiteSpace($env:NEXORA_RECOVERY_DIR)) {
    Write-Host ("Recuperacion a revisar: " + $env:NEXORA_RECOVERY_DIR) -ForegroundColor Yellow
}
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
            $Live.phase = if ($ExitCode -eq 0) { "Sesion de auditoria detenida" } else { "Bloqueo de ejecucion" }
            $Live.task = if ($ExitCode -eq 0) { "OpenCode termino la sesion sin activar la puerta final" } else { "OpenCode termino con error" }
            $Live.detail = "Codigo de salida: $ExitCode"
            $Live.blocking_issue = if ($ExitCode -eq 0) { "La auditoria continua pendiente hasta que audit_cli.js gate apruebe." } else { "Revise el error de OpenCode antes de continuar." }
            $Live.last_update = (Get-Date).ToUniversalTime().ToString("o")
            Write-JsonUtf8 -Path $LivePath -Value $Live
        }
    }
    catch {}

    Add-Content -Path $LogPath -Encoding UTF8 -Value ("OpenCode termino con codigo " + $ExitCode + ": " + (Get-Date).ToString("s"))
}

$AwaitingReview = $false
try {
    $FinalLive = Get-Content -Raw -Path $LivePath | ConvertFrom-Json
    $AwaitingReview = $FinalLive.agent_status -eq "awaiting_review"
}
catch {}

if ($AwaitingReview) {
    Write-Host "Verificando la puerta final independiente..." -ForegroundColor Cyan
    & bun $FinalGateCheck
    $GateExitCode = $LASTEXITCODE
    if ($GateExitCode -eq 0) {
        Write-Host "Puerta final aprobada. Abriendo ventana de autorizacion..." -ForegroundColor Green
        $FinalArgs = "-NoExit -ExecutionPolicy Bypass -File `"$FinalAuthorization`""
        Start-Process powershell.exe -ArgumentList $FinalArgs
    }
    else {
        Write-Host "OpenCode solicito revision, pero la puerta final sigue bloqueada." -ForegroundColor Red
        Write-Host "Revise .nexora-monitor\final-gate.json y continue la correccion." -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "OpenCode termino con codigo $ExitCode." -ForegroundColor Yellow
Write-Host "El monitor permanece disponible en http://127.0.0.1:8765" -ForegroundColor Cyan
Write-Host "La fusion permanece bloqueada." -ForegroundColor Red
