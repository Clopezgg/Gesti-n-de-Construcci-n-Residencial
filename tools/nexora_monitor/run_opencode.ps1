$ErrorActionPreference = "Stop"

[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [System.Text.UTF8Encoding]::new()
try { chcp 65001 | Out-Null } catch {}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$RuntimeDir = Join-Path $RepoRoot ".nexora-monitor"
$SessionPath = Join-Path $RuntimeDir "session.json"
$LogPath = Join-Path $RuntimeDir "opencode-live.log"
$PromptPath = Join-Path $RuntimeDir "session-prompt.txt"
$StallMarkerPath = Join-Path $RuntimeDir "opencode-stall.json"
$LivePath = Join-Path $RepoRoot "docs\nexora\LIVE_PROGRESS.json"
$ResultsPath = Join-Path $RepoRoot "docs\nexora\AUDIT_RESULTS.json"
$DefectsPath = Join-Path $RepoRoot "docs\nexora\DEFECTS.json"
$CheckpointPath = Join-Path $RepoRoot "docs\nexora\CHECKPOINT.md"
$AuditCli = Join-Path $PSScriptRoot "audit_cli.js"
$AuditUpdate = Join-Path $PSScriptRoot "audit_update.js"
$AuditMandate = Join-Path $RepoRoot "docs\nexora\OPENCODE_AUDIT_MANDATE.md"
$FinalGateCheck = Join-Path $PSScriptRoot "final_gate_check.js"
$FinalAuthorization = Join-Path $PSScriptRoot "final_authorization.ps1"
$MaxSessions = 80
$MaxStallRestarts = 3
$StallMinutes = 20
Set-Location $RepoRoot
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null

function Write-JsonUtf8 {
    param(
        [Parameter(Mandatory = $true)] [string] $Path,
        [Parameter(Mandatory = $true)] $Value
    )
    $Encoding = [System.Text.UTF8Encoding]::new($false)
    $Json = $Value | ConvertTo-Json -Depth 40
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

function Get-ResumeState {
    $Raw = (& bun $AuditCli resume 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo calcular el punto de reanudacion: $Raw"
    }
    try {
        return $Raw | ConvertFrom-Json
    }
    catch {
        throw "audit_cli resume no devolvio JSON valido: $Raw"
    }
}

function Get-ProgressSignature {
    $Parts = @()
    foreach ($Path in @($ResultsPath, $DefectsPath, $LivePath, $CheckpointPath)) {
        if (Test-Path $Path) {
            $Item = Get-Item $Path
            $Parts += ($Path + "|" + $Item.Length + "|" + $Item.LastWriteTimeUtc.Ticks)
        }
        else {
            $Parts += ($Path + "|missing")
        }
    }
    return ($Parts -join ";")
}

function New-AuditCheckpoint {
    param(
        [Parameter(Mandatory = $true)] [int] $SessionNumber,
        [Parameter(Mandatory = $true)] $ResumeState,
        [Parameter(Mandatory = $true)] [string] $Reason
    )

    $Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $Directory = Join-Path $RuntimeDir ("checkpoints\" + $Stamp + "-s" + $SessionNumber)
    $Worktree = Join-Path $Directory "worktree"
    New-Item -ItemType Directory -Force -Path $Worktree | Out-Null

    $CriticalFiles = @(
        "EXECUTION_STATE.md",
        "docs\nexora\MATRIZ_REQUISITOS.md",
        "docs\nexora\CHECKPOINT.md",
        "docs\nexora\AUDIT_RESULTS.json",
        "docs\nexora\DEFECTS.json",
        "docs\nexora\LIVE_PROGRESS.json",
        "docs\nexora\FINAL_REVIEW_PACKAGE.md"
    )

    $ChangedFiles = @()
    $ChangedFiles += @(git diff --name-only)
    $ChangedFiles += @(git diff --cached --name-only)
    $ChangedFiles += @(git ls-files --others --exclude-standard)

    $Files = @(
        $CriticalFiles + $ChangedFiles |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
        Sort-Object -Unique
    )

    $Copied = @()
    foreach ($RelativePath in $Files) {
        if (-not (Test-Path -LiteralPath $RelativePath)) { continue }
        $Destination = Join-Path $Worktree $RelativePath
        $DestinationParent = Split-Path $Destination -Parent
        New-Item -ItemType Directory -Force -Path $DestinationParent | Out-Null
        Copy-Item -LiteralPath $RelativePath -Destination $Destination -Force
        $Hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $RelativePath).Hash
        $Copied += [pscustomobject]@{
            path = $RelativePath
            sha256 = $Hash
        }
    }

    $Manifest = [ordered]@{
        schema_version = 1
        created_at = (Get-Date).ToUniversalTime().ToString("o")
        reason = $Reason
        session_number = $SessionNumber
        head = (git rev-parse HEAD).Trim()
        branch = (git branch --show-current).Trim()
        resume = $ResumeState
        files = $Copied
    }
    Write-JsonUtf8 -Path (Join-Path $Directory "manifest.json") -Value $Manifest

    git status --short |
        Set-Content -Path (Join-Path $Directory "git-status.txt") -Encoding UTF8
    git diff --stat |
        Set-Content -Path (Join-Path $Directory "git-diff-stat.txt") -Encoding UTF8
    & bun $AuditCli summary 2>&1 |
        Set-Content -Path (Join-Path $Directory "audit-summary.txt") -Encoding UTF8

    [System.IO.File]::WriteAllText(
        (Join-Path $RuntimeDir "latest-checkpoint.txt"),
        $Directory,
        [System.Text.UTF8Encoding]::new($false)
    )

    Add-Content -Path $LogPath -Encoding UTF8 -Value (
        "Checkpoint creado: " + $Directory + " | razon: " + $Reason
    )
    return $Directory
}

function Start-StallWatchdog {
    param(
        [Parameter(Mandatory = $true)] [int] $RunnerPid,
        [Parameter(Mandatory = $true)] [string] $RepositoryRoot,
        [Parameter(Mandatory = $true)] [int] $Minutes,
        [Parameter(Mandatory = $true)] [string] $MarkerPath
    )

    return Start-Job -ArgumentList $RunnerPid, $RepositoryRoot, $Minutes, $MarkerPath -ScriptBlock {
        param($ParentPid, $Root, $StallLimitMinutes, $Marker)

        function Signature {
            $Paths = @(
                (Join-Path $Root "docs\nexora\AUDIT_RESULTS.json"),
                (Join-Path $Root "docs\nexora\DEFECTS.json"),
                (Join-Path $Root "docs\nexora\LIVE_PROGRESS.json"),
                (Join-Path $Root "docs\nexora\CHECKPOINT.md")
            )
            $Parts = @()
            foreach ($Path in $Paths) {
                if (Test-Path $Path) {
                    $Item = Get-Item $Path
                    $Parts += ($Path + "|" + $Item.Length + "|" + $Item.LastWriteTimeUtc.Ticks)
                }
                else {
                    $Parts += ($Path + "|missing")
                }
            }
            return ($Parts -join ";")
        }

        function Descendants {
            param([int] $RootPid)
            $All = @(Get-CimInstance Win32_Process)
            $Known = @($RootPid)
            $Result = @()
            $Changed = $true
            while ($Changed) {
                $Changed = $false
                foreach ($Process in $All) {
                    if ($Known -contains [int] $Process.ProcessId) { continue }
                    if ($Known -contains [int] $Process.ParentProcessId) {
                        $Known += [int] $Process.ProcessId
                        $Result += $Process
                        $Changed = $true
                    }
                }
            }
            return $Result
        }

        $LastSignature = Signature
        $LastProgress = Get-Date
        $TargetPid = $null

        while ($true) {
            Start-Sleep -Seconds 15
            $Current = Signature
            if ($Current -ne $LastSignature) {
                $LastSignature = $Current
                $LastProgress = Get-Date
            }

            $Children = @(Descendants -RootPid $ParentPid)
            $OpenCode = @(
                $Children |
                Where-Object {
                    $_.Name -match "opencode" -or
                    $_.CommandLine -match "(^|[\\/\s])opencode(\.cmd|\.exe)?(\s|$)" -or
                    $_.CommandLine -match "opencode-ai"
                }
            ) | Select-Object -First 1

            if (-not $OpenCode) {
                $OpenCode = @(
                    $Children |
                    Where-Object {
                        $_.Name -match "^(bun|node|cmd)\.exe$" -and
                        $_.CommandLine -notmatch "dashboard_server_v3"
                    } |
                    Sort-Object CreationDate -Descending
                ) | Select-Object -First 1
            }

            if ($OpenCode) {
                $TargetPid = [int] $OpenCode.ProcessId
            }

            if (((Get-Date) - $LastProgress).TotalMinutes -lt $StallLimitMinutes) {
                continue
            }

            $Event = [ordered]@{
                schema_version = 1
                detected_at = (Get-Date).ToUniversalTime().ToString("o")
                reason = "Sin cambios persistidos durante $StallLimitMinutes minutos."
                runner_pid = $ParentPid
                opencode_pid = $TargetPid
                last_progress_at = $LastProgress.ToUniversalTime().ToString("o")
            }
            $Encoding = [System.Text.UTF8Encoding]::new($false)
            [System.IO.File]::WriteAllText(
                $Marker,
                ($Event | ConvertTo-Json -Depth 10),
                $Encoding
            )

            if ($TargetPid) {
                & taskkill.exe /PID $TargetPid /T /F | Out-Null
            }
            break
        }
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

Write-Host "Inicializando o reanudando auditoria para HEAD $Head..." -ForegroundColor Cyan
& bun $AuditCli init $Head
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo inicializar AUDIT_RESULTS.json."
}

& bun $AuditCli validate
if ($LASTEXITCODE -ne 0) {
    throw "Los archivos canonicos de auditoria no son validos."
}

if (-not (Test-Path $LogPath)) {
    [System.IO.File]::WriteAllText(
        $LogPath,
        ("OpenCode auditoria por capas iniciada: " + (Get-Date).ToString("s") + "`r`n"),
        [System.Text.UTF8Encoding]::new($false)
    )
}
Add-Content -Path $LogPath -Encoding UTF8 -Value (
    "Reanudacion iniciada: " + (Get-Date).ToString("s") + " | HEAD: " + $Head
)

$Session = [ordered]@{
    schema_version = 2
    status = "running"
    started_at = (Get-Date).ToUniversalTime().ToString("o")
    finished_at = $null
    exit_code = $null
    branch = "nexora-continuidad-total"
    pull_request = 12
    head = $Head
    mode = "OpenCode bounded layered audit sessions"
    session_number = 0
    active_block = $null
    recovery_dir = $env:NEXORA_RECOVERY_DIR
    latest_checkpoint = $null
    stall_restarts = 0
}
Write-JsonUtf8 -Path $SessionPath -Value $Session

$StallRestarts = 0
$FinalExitCode = 0
$StopReason = ""

for ($SessionNumber = 1; $SessionNumber -le $MaxSessions; $SessionNumber++) {
    $Resume = Get-ResumeState
    $Session.session_number = $SessionNumber
    $Session.active_block = $Resume.next.block
    Write-JsonUtf8 -Path $SessionPath -Value $Session

    if ($Resume.gate_ready) {
        $StopReason = "La puerta de auditoria ya esta lista."
        break
    }

    $CheckpointDirectory = New-AuditCheckpoint `
        -SessionNumber $SessionNumber `
        -ResumeState $Resume `
        -Reason "Inicio de sesion acotada"

    $Session.latest_checkpoint = $CheckpointDirectory
    Write-JsonUtf8 -Path $SessionPath -Value $Session

    $BeforeExecuted = [int] $Resume.metrics.executed
    $BeforeSignature = Get-ProgressSignature
    $NextRequirement = if ($Resume.next.requirement_id) { $Resume.next.requirement_id } else { "sin requisito" }
    $NextValidation = if ($Resume.next.validation_id) { $Resume.next.validation_id } else { "sin validacion" }

    $Prompt = @"
SIRILAN autorizo continuar la auditoria completa, pero esta es una SESION ACOTADA Y REANUDABLE.

ESTADO PERSISTIDO:
- HEAD local: $Head
- Sesion acotada: $SessionNumber
- Auditoria: $($Resume.metrics.audit_percent)% ($($Resume.metrics.executed)/$($Resume.metrics.total))
- Certificacion: $($Resume.metrics.certification_percent)%
- Requisitos certificados: $($Resume.metrics.requirements_certified)/$($Resume.metrics.requirements_total)
- Bloques certificados: $($Resume.metrics.blocks_certified)/$($Resume.metrics.blocks_total)
- Siguiente bloque: $($Resume.next.block)
- Siguiente requisito: $NextRequirement
- Siguiente validacion: $NextValidation
- Checkpoint previo: $CheckpointDirectory

REANUDACION OBLIGATORIA:
1. Lee AGENTS.md y todos los documentos maestros indicados en docs/nexora/OPENCODE_AUDIT_MANDATE.md.
2. Lee AUDIT_RESULTS.json, DEFECTS.json, LIVE_PROGRESS.json, CHECKPOINT.md, git status y git diff.
3. No reinicies la auditoria, no borres resultados y no repitas validaciones certified/not_applicable salvo regresion concreta.
4. Confirma el ultimo resultado persistido y comienza exactamente en el primer punto no final indicado por audit_cli.js resume.
5. Usa audit_update.js. No edites a mano estados certificados sin detalle, evidencia y SHA completo.
6. Conserva todo cambio local y revisa cualquier carpeta de recuperacion o checkpoint antes de sobrescribir.
7. No uses reset, restore, clean, force push, merge, borrado de ramas, main, produccion, AWS, Coolify ni DNS.

LIMITE DE ESTA SESION:
- Procesa como maximo 20 requisitos o 120 validaciones, lo que ocurra primero.
- Actualiza LIVE_PROGRESS.json antes y despues de cada requisito, prueba, correccion, commit, push y CI.
- Cuando el indicador de contexto llegue a 70%, deja de iniciar trabajo nuevo.
- Antes de terminar, valida los JSON, actualiza CHECKPOINT.md, ejecuta audit_cli.js resume y deja un resumen exacto.
- Luego termina esta sesion limpiamente para que el supervisor abra una nueva con contexto fresco.
- Si una tarea larga esta ejecutandose, registra heartbeat en LIVE_PROGRESS.json al menos cada 5 minutos.

La puerta final, fusion, tags, despliegue y eliminacion de ramas siguen bloqueados.
"@

    [System.IO.File]::WriteAllText(
        $PromptPath,
        $Prompt,
        [System.Text.UTF8Encoding]::new($false)
    )

    Update-LiveProgress `
        -AgentStatus "working" `
        -Phase ("Auditoria reanudada - Bloque " + $Resume.next.block) `
        -CurrentBlock $Resume.next.block `
        -Task ("Continuando desde " + $NextRequirement + " / " + $NextValidation) `
        -Detail ("Sesion acotada " + $SessionNumber + ". Auditoria " + $Resume.metrics.audit_percent + "%.") `
        -BlockingIssue ""

    Write-Host ""
    Write-Host "NEXORA - OpenCode Auditor por Capas" -ForegroundColor Cyan
    Write-Host ("Sesion acotada: " + $SessionNumber + " de " + $MaxSessions) -ForegroundColor Green
    Write-Host ("HEAD: " + $Head) -ForegroundColor Green
    Write-Host ("Auditoria recuperada: " + $Resume.metrics.audit_percent + "%") -ForegroundColor Green
    Write-Host ("Continuando en Bloque " + $Resume.next.block + " / " + $NextRequirement) -ForegroundColor Yellow
    Write-Host ("Checkpoint: " + $CheckpointDirectory) -ForegroundColor Cyan
    Write-Host ("Watchdog: " + $StallMinutes + " minutos sin cambios persistidos.") -ForegroundColor Yellow
    Write-Host ""

    if (Test-Path $StallMarkerPath) {
        Remove-Item -Path $StallMarkerPath -Force
    }

    $WatchdogJob = Start-StallWatchdog `
        -RunnerPid $PID `
        -RepositoryRoot $RepoRoot `
        -Minutes $StallMinutes `
        -MarkerPath $StallMarkerPath

    $ExitCode = 1
    try {
        $ShortPrompt = "Lee .nexora-monitor/session-prompt.txt y ejecuta exactamente sus instrucciones."
        & opencode --auto --prompt $ShortPrompt
        $ExitCode = $LASTEXITCODE
    }
    finally {
        if ($WatchdogJob) {
            Stop-Job -Job $WatchdogJob -ErrorAction SilentlyContinue
            Remove-Job -Job $WatchdogJob -ErrorAction SilentlyContinue
        }
    }

    $After = Get-ResumeState
    $AfterExecuted = [int] $After.metrics.executed
    $AfterSignature = Get-ProgressSignature
    $MadeProgress = ($AfterExecuted -gt $BeforeExecuted) -or ($AfterSignature -ne $BeforeSignature)
    $WasStalled = Test-Path $StallMarkerPath

    $CheckpointReason = if ($WasStalled) {
        "Watchdog detecto sesion atascada"
    }
    else {
        "Fin de sesion acotada"
    }

    New-AuditCheckpoint `
        -SessionNumber $SessionNumber `
        -ResumeState $After `
        -Reason $CheckpointReason |
        Out-Null

    Add-Content -Path $LogPath -Encoding UTF8 -Value (
        "Sesion " + $SessionNumber +
        " termino con codigo " + $ExitCode +
        " | progreso: " + $BeforeExecuted + " -> " + $AfterExecuted +
        " | stall: " + $WasStalled
    )

    if ($After.gate_ready) {
        $StopReason = "La auditoria alcanzo la puerta final."
        $FinalExitCode = 0
        break
    }

    if ($WasStalled) {
        $StallRestarts += 1
        $Session.stall_restarts = $StallRestarts
        Write-JsonUtf8 -Path $SessionPath -Value $Session

        Update-LiveProgress `
            -AgentStatus "working" `
            -Phase "Recuperacion automatica de sesion atascada" `
            -CurrentBlock $After.next.block `
            -Task "Abriendo una nueva sesion desde el ultimo checkpoint" `
            -Detail ("El watchdog conservo el avance y reiniciara con contexto fresco. Intento " + $StallRestarts + ".") `
            -BlockingIssue ""

        if ($StallRestarts -ge $MaxStallRestarts -and -not $MadeProgress) {
            $StopReason = "Tres sesiones consecutivas se atascaron sin progreso persistido."
            $FinalExitCode = 124
            break
        }

        Start-Sleep -Seconds 5
        continue
    }

    if ($MadeProgress) {
        $StallRestarts = 0
        $Session.stall_restarts = 0
        Write-JsonUtf8 -Path $SessionPath -Value $Session
        Start-Sleep -Seconds 3
        continue
    }

    if ($ExitCode -ne 0) {
        $StopReason = "OpenCode termino con error y no dejo progreso nuevo."
        $FinalExitCode = $ExitCode
        break
    }

    $StopReason = "OpenCode termino sin error, pero no persistio progreso nuevo."
    $FinalExitCode = 125
    break
}

if ([string]::IsNullOrWhiteSpace($StopReason)) {
    $StopReason = "Se alcanzo el limite de sesiones acotadas."
    $FinalExitCode = 126
}

$Session.status = if ($FinalExitCode -eq 0) { "finished" } else { "blocked" }
$Session.finished_at = (Get-Date).ToUniversalTime().ToString("o")
$Session.exit_code = $FinalExitCode
$Session.stop_reason = $StopReason
Write-JsonUtf8 -Path $SessionPath -Value $Session

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
elseif ($FinalExitCode -ne 0) {
    Update-LiveProgress `
        -AgentStatus "blocked" `
        -Phase "Auditoria detenida con avance protegido" `
        -CurrentBlock $Session.active_block `
        -Task "Revisar el motivo de detencion antes de continuar" `
        -Detail $StopReason `
        -BlockingIssue "El checkpoint mas reciente permanece guardado."
}

Write-Host ""
Write-Host $StopReason -ForegroundColor Yellow
Write-Host ("Codigo final: " + $FinalExitCode) -ForegroundColor Yellow
Write-Host "El avance permanece en AUDIT_RESULTS.json y en .nexora-monitor\checkpoints." -ForegroundColor Green
Write-Host "La fusion permanece bloqueada." -ForegroundColor Red
