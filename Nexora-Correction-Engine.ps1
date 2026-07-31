# ==========================================================
# NEXORA CORRECTION ENGINE
# AUDIT + SAFE REPAIR + VALIDATION
# ==========================================================

Clear-Host

$ErrorActionPreference="Stop"


Write-Host "
====================================================
 NEXORA CORRECTION ENGINE
 SAFE ENTERPRISE REPAIR SYSTEM
====================================================
" -ForegroundColor Cyan


$project=(Get-Location).Path


$branch=git branch --show-current

$sha=git rev-parse HEAD



Write-Host "
Proyecto:
$project

Branch:
$branch

SHA:
$sha
"



# ------------------------------------------------------
# ENGINE STORAGE
# ------------------------------------------------------

$engine=".nexora-engine"


New-Item "$engine\logs" -ItemType Directory -Force | Out-Null
New-Item "$engine\reports" -ItemType Directory -Force | Out-Null
New-Item "$engine\backup" -ItemType Directory -Force | Out-Null



function Log($msg){

$time=Get-Date

"$time | $msg" |
Out-File "$engine\logs\engine.log" -Append

Write-Host $msg

}



# ------------------------------------------------------
# VERIFY REPOSITORY
# ------------------------------------------------------


Log "Verificando repositorio"


if(!(Test-Path ".git")){

throw "No es un repositorio Git"

}



# ------------------------------------------------------
# CREATE SAFETY TAG
# ------------------------------------------------------


Log "Creando punto seguro"


git tag "nexora-before-engine-$((Get-Date).ToString('yyyyMMddHHmm'))"



# ------------------------------------------------------
# EXECUTION STATE
# ------------------------------------------------------


@"

# NEXORA EXECUTION STATE

Fecha:
$(Get-Date)

SHA Inicial:
$sha

Estado:

AUDITORIA INICIADA

Bloques:

[ ] Arquitectura
[ ] Backend
[ ] Frontend
[ ] Seguridad
[ ] Finanzas
[ ] Construccion
[ ] Inventario
[ ] Testing


"@ | Out-File EXECUTION_STATE.md



# ------------------------------------------------------
# PYTHON VALIDATION
# ------------------------------------------------------


Log "Validando Python"


python --version


python -m compileall nexora_app `
-exclude venv `
> "$engine\reports\python-check.txt"



if($LASTEXITCODE -eq 0){

Log "Python OK"

}else{

Log "Python tiene errores revisar"

}




# ------------------------------------------------------
# SEARCH ERRORS
# ------------------------------------------------------


Log "Buscando problemas conocidos"



$patterns=@(

"TODO",
"FIXME",
"pass #",
"NotImplemented",
"localhost",
"password=",
"secret=",
"api_key"

)



foreach($p in $patterns){


Write-Host "
Buscando:
$p
"


Select-String `
-Path .\nexora_app\* `
-Pattern $p `
-Recurse `
-ErrorAction SilentlyContinue `
>> "$engine\reports\findings.txt"


}



# ------------------------------------------------------
# DEPENDENCY CHECK
# ------------------------------------------------------


Log "Revisando dependencias"



if(Test-Path "pyproject.toml"){

python -m pip check `
>> "$engine\reports\dependencies.txt"

}



if(Test-Path "package.json"){

npm audit `
--omit=dev `
>> "$engine\reports\npm-audit.txt"


}



# ------------------------------------------------------
# GIT CLEAN CHECK
# ------------------------------------------------------


Log "Estado Git"


git status



# ------------------------------------------------------
# SAVE REPORT
# ------------------------------------------------------


@"

====================================================
NEXORA ENGINE REPORT
====================================================


Proyecto:

$project


SHA:

$sha


Fecha:

$(Get-Date)


Resultado:

AUDITORIA EJECUTADA


Siguiente fase:

CORRECCION CONTROLADA POR MODULOS


====================================================


"@ | Out-File "$engine\reports\FINAL.md"



# ------------------------------------------------------
# COMMIT
# ------------------------------------------------------


git add .



git commit `
-m "NEXORA engine audit checkpoint"



git push origin $branch



Write-Host "
====================================================
 NEXORA ENGINE BLOQUE 1 COMPLETADO
====================================================

SIGUIENTE:

Analizar reportes:

.nexora-engine/reports/

Luego iniciar:

MODULO 1
ARQUITECTURA

====================================================
" -ForegroundColor Green