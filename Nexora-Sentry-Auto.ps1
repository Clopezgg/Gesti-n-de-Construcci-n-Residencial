# ==========================================================
# NEXORA SENTRY AUTO INTEGRATION
# Frappe / ERPNext
# ==========================================================

Clear-Host

$ErrorActionPreference="Stop"

Write-Host "======================================"
Write-Host " NEXORA SENTRY AUTO INTEGRATION"
Write-Host "======================================"


$Project = Get-Location


Write-Host ""
Write-Host "Proyecto:"
Write-Host $Project



# Buscar app Nexora

$hooks = Get-ChildItem -Recurse -Filter hooks.py |
Where-Object {
    $_.FullName -match "nexora_app"
}



if(!$hooks)
{
    Write-Host "No se encontró hooks.py de Nexora"
    exit
}


$hooksPath = $hooks.FullName


Write-Host ""
Write-Host "Hooks encontrado:"
Write-Host $hooksPath



# Carpeta nexora

$nexoraFolder = Split-Path $hooksPath



# Crear sentry.py

$sentryFile="$nexoraFolder\sentry.py"


if(!(Test-Path $sentryFile))
{

@'
import os
import sentry_sdk


def init_sentry():

    dsn = os.getenv("SENTRY_DSN")

    if not dsn:
        return


    sentry_sdk.init(
        dsn=dsn,
        send_default_pii=True,
        traces_sample_rate=1.0,
    )
'@ | Out-File $sentryFile -Encoding UTF8


Write-Host "Creado sentry.py"

}
else
{
Write-Host "sentry.py ya existe"
}




# Modificar hooks.py


$hooksContent = Get-Content $hooksPath -Raw


if($hooksContent -notmatch "app_ready")
{

Add-Content $hooksPath @"


app_ready = [
    "nexora.sentry.init_sentry"
]

"@


Write-Host "hooks.py actualizado"

}
else
{
Write-Host "hooks.py ya tenía app_ready"
}




# Instalar Sentry

Write-Host ""
Write-Host "Instalando Sentry SDK"


if(Get-Command python -ErrorAction SilentlyContinue)
{

python -m pip install sentry-sdk

}
else
{
Write-Host "Python no encontrado"
}





# DSN

Write-Host ""

$dsn = Read-Host "Pega tu DSN Sentry"



@"
SENTRY_DSN=$dsn
"@ | Out-File ".env.sentry" -Encoding UTF8



# Reporte

$report=@"

====================================
NEXORA SENTRY REPORT
====================================

Proyecto:

$Project


Hooks:

$hooksPath


Sentry:

ACTIVADO


Fecha:

$(Get-Date)


====================================

"@


$report | Out-File "nexora-sentry-report.txt"



Write-Host ""
Write-Host "======================================"
Write-Host " TERMINADO"
Write-Host "======================================"

Write-Host ""
Write-Host "Archivos creados:"
Write-Host $sentryFile
Write-Host ".env.sentry"
Write-Host "nexora-sentry-report.txt"


Pause