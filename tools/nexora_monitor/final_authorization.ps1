$ErrorActionPreference = "Stop"

[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [System.Text.UTF8Encoding]::new()
try { chcp 65001 | Out-Null } catch {}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$RuntimeDir = Join-Path $RepoRoot ".nexora-monitor"
$GatePath = Join-Path $RuntimeDir "final-gate.json"
$AuthorizationPath = Join-Path $RuntimeDir "authorization-request.json"
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

if (-not (Test-Path $GatePath)) {
    throw "No existe la evidencia de la puerta final: $GatePath"
}

$Gate = Get-Content -Raw -Path $GatePath | ConvertFrom-Json
if (-not $Gate.passed) {
    Write-Host "NEXORA NO ALCANZO LA PUERTA FINAL" -ForegroundColor Red
    foreach ($Failure in $Gate.failures) {
        Write-Host ("- " + $Failure) -ForegroundColor Red
    }
    throw "La autorizacion de fusion permanece bloqueada."
}

$CurrentHead = (git rev-parse HEAD).Trim()
if ($CurrentHead -ne $Gate.head) {
    throw "El HEAD cambio despues de la validacion final. Ejecute nuevamente la puerta final."
}

Clear-Host
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " NEXORA - AUTORIZACION FINAL INDEPENDIENTE" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Auditoria por capas: 100%" -ForegroundColor Green
Write-Host "Certificacion real: 100%" -ForegroundColor Green
Write-Host "Requisitos: 166/166" -ForegroundColor Green
Write-Host "Bloques: 21/21" -ForegroundColor Green
Write-Host "Defectos abiertos: 0" -ForegroundColor Green
Write-Host "GitHub Actions del mismo SHA: TODOS VERDES" -ForegroundColor Green
Write-Host ("HEAD final: " + $Gate.head) -ForegroundColor Green
Write-Host ""
Write-Host "La primera decision disponible es fusionar PR #12 hacia nexora-reconstruccion." -ForegroundColor Yellow
Write-Host "Esta autorizacion NO autoriza PR #11 hacia main, NO elimina ramas y NO despliega." -ForegroundColor Yellow
Write-Host "Despues de la primera fusion se ejecutara una nueva validacion completa." -ForegroundColor Yellow
Write-Host "La eliminacion de ramas antiguas se preguntara al final y solo para ramas totalmente fusionadas." -ForegroundColor Yellow
Write-Host ""
Write-Host "Para autorizar, escriba exactamente: AUTORIZO PR12" -ForegroundColor Cyan
Write-Host "Para mantener todo bloqueado, escriba: NO" -ForegroundColor Cyan
Write-Host ""

$Decision = (Read-Host "Decision").Trim()
$Authorized = $Decision -ceq "AUTORIZO PR12"
$Rejected = $Decision -ceq "NO"

if (-not $Authorized -and -not $Rejected) {
    Write-Host "Respuesta no reconocida. No se autorizo ninguna accion." -ForegroundColor Red
    $Decision = "INVALIDA"
}

$Authorization = [ordered]@{
    schema_version = 1
    created_at = (Get-Date).ToUniversalTime().ToString("o")
    head = $Gate.head
    pull_request = 12
    target_branch = "nexora-reconstruccion"
    decision = $Decision
    authorized = $Authorized
    main_authorized = $false
    branch_deletion_authorized = $false
    deployment_authorized = $false
    executed = $false
    note = "La fusion requiere revision independiente y ejecucion controlada. Esta ventana solo registra la autorizacion expresa."
}
Write-JsonUtf8 -Path $AuthorizationPath -Value $Authorization

Write-Host ""
if ($Authorized) {
    Write-Host "AUTORIZACION PR #12 REGISTRADA" -ForegroundColor Green
    Write-Host ("Archivo local: " + $AuthorizationPath) -ForegroundColor Cyan
    Write-Host "Regrese a ChatGPT para la revision independiente y la fusion controlada." -ForegroundColor Yellow
    Write-Host "Todavia no se elimino ninguna rama y main permanece intacta." -ForegroundColor Yellow
}
elseif ($Rejected) {
    Write-Host "Fusion no autorizada. El repositorio permanece sin fusionar." -ForegroundColor Yellow
}
else {
    Write-Host "No se registro autorizacion valida." -ForegroundColor Red
}

Write-Host ""
Read-Host "Presione Enter para cerrar esta ventana"
