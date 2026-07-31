# ============================================================
# NEXORA MASTER AUDIT & RECOVERY AGENT
# Enterprise Repository Auditor
# ============================================================

Clear-Host

$ErrorActionPreference="Stop"


Write-Host "
====================================================
 NEXORA MASTER AUDIT AGENT
 AUDITORIA + CORRECCION + CONSOLIDACION
====================================================
" -ForegroundColor Cyan


# ----------------------------------------------------
# VALIDAR REPOSITORIO
# ----------------------------------------------------

if(!(Test-Path ".git"))
{
    Write-Host "ERROR: No estas dentro del repositorio Git"
    exit
}


$repo = git remote get-url origin

$branch = git branch --show-current

$sha = git rev-parse HEAD


Write-Host "
Repositorio:
$repo

Rama:
$branch

SHA:
$sha
"


# ----------------------------------------------------
# CREAR ESTADO
# ----------------------------------------------------

$state="EXECUTION_STATE.md"


if(!(Test-Path $state))
{

@"

# NEXORA EXECUTION STATE

Inicio:
$(Get-Date)

Repositorio:
$repo

SHA inicial:
$sha


Estado:

AUDITORIA INICIAL


"@ | Out-File $state

}



# ----------------------------------------------------
# BACKUP TAG
# ----------------------------------------------------

git tag "backup-before-audit-$(Get-Date -Format yyyyMMddHHmm)"



# ----------------------------------------------------
# ESTRUCTURA
# ----------------------------------------------------

Write-Host "
[1] Analizando arquitectura
"


$files = Get-ChildItem -Recurse -File |
Measure-Object


$python =
Get-ChildItem -Recurse -Filter "*.py" |
Measure-Object


$js =
Get-ChildItem -Recurse -Filter "*.js" |
Measure-Object


$css =
Get-ChildItem -Recurse -Filter "*.css" |
Measure-Object



@"

# AUDITORIA TECNICA

Fecha:
$(Get-Date)


Archivos totales:
$($files.Count)


Python:
$($python.Count)


Javascript:
$($js.Count)


CSS:
$($css.Count)


"@ | Out-File "NEXORA-AUDIT-REPORT.md"



# ----------------------------------------------------
# DETECTAR ARCHIVOS IMPORTANTES
# ----------------------------------------------------

Write-Host "
[2] Buscando arquitectura Nexora
"


$important=@(
"hooks.py",
"pyproject.toml",
"package.json",
"hooks.js",
"requirements.txt",
"EXECUTION_STATE.md"
)



foreach($item in $important)
{

$result=Get-ChildItem -Recurse -Filter $item

if($result)
{
Add-Content "NEXORA-AUDIT-REPORT.md" "
CONFIRMADO:
$item
"
}
else
{
Add-Content "NEXORA-AUDIT-REPORT.md" "
NO ENCONTRADO:
$item
"
}

}



# ----------------------------------------------------
# SEGURIDAD
# ----------------------------------------------------

Write-Host "
[3] Revisando secretos
"


$secret=Get-ChildItem -Recurse -File |
Select-String -Pattern "password|secret|apikey|token" -ErrorAction SilentlyContinue


if($secret)
{

$secret |
Out-File "SECURITY-FINDINGS.txt"

}



# ----------------------------------------------------
# TEST PYTHON
# ----------------------------------------------------

Write-Host "
[4] Probando Python
"


python -c "
import sentry_sdk
print('Python OK')
"



# ----------------------------------------------------
# TEST GIT
# ----------------------------------------------------


Write-Host "
[5] Estado Git
"


git status



# ----------------------------------------------------
# ACTUALIZAR ESTADO
# ----------------------------------------------------


Add-Content $state "

## Auditoria ejecutada

Fecha:
$(Get-Date)

SHA:
$sha

Reportes generados:

- NEXORA-AUDIT-REPORT.md
- SECURITY-FINDINGS.txt


"



# ----------------------------------------------------
# COMMIT
# ----------------------------------------------------


git add .


git commit -m "NEXORA audit baseline and execution state"



git push origin $branch



Write-Host "

====================================================
 AUDITORIA BASE COMPLETADA
====================================================


SIGUIENTE FASE:

Analizar NEXORA-AUDIT-REPORT.md

Luego:

1. Arquitectura
2. Backend
3. Frontend
4. Seguridad
5. Finanzas
6. Construccion
7. Inventario
8. Pruebas


SHA NUEVO:

"

git rev-parse HEAD