# ==========================================================
# NEXORA SENTRY FINAL SETUP
# Frappe + Python + JavaScript + GitHub
# ==========================================================

Clear-Host

Write-Host "======================================" -ForegroundColor Cyan
Write-Host " NEXORA SENTRY FINAL SETUP"
Write-Host "======================================" -ForegroundColor Cyan


# Verificar ubicación
$project = Get-Location

Write-Host ""
Write-Host "Proyecto:"
Write-Host $project


# DSN Sentry
$DSN = "https://a0925cf9dcdc3feae0e225bb50d04fa1@o4511830522265600.ingest.us.sentry.io/4511830661529600"


# ----------------------------------------------------------
# PYTHON SENTRY
# ----------------------------------------------------------

Write-Host ""
Write-Host "[1] Verificando Sentry Python"

python -m pip install sentry-sdk


# Crear archivo sentry.py si no existe
$sentryFile = ".\nexora_app\nexora\sentry.py"

@"
import sentry_sdk
import os

def init_sentry():

    sentry_sdk.init(
        dsn=os.getenv(
            "SENTRY_DSN",
            "$DSN"
        ),

        send_default_pii=True,

        traces_sample_rate=1.0,

        environment="nexora"
    )
"@ | Out-File $sentryFile -Encoding UTF8


Write-Host "Backend Sentry actualizado"


# ----------------------------------------------------------
# JAVASCRIPT SENTRY
# ----------------------------------------------------------

Write-Host ""
Write-Host "[2] Creando Sentry Frontend"


$jsFile = ".\nexora_app\nexora\public\js\nexora_sentry.js"


@"
(function(){

    var script=document.createElement("script");

    script.src=
    "https://browser.sentry-cdn.com/10.1.0/bundle.min.js";


    script.onload=function(){

        Sentry.init({

            dsn:"$DSN",

            environment:"nexora",

            tracesSampleRate:1.0

        });


        console.log(
        "NEXORA SENTRY FRONTEND ACTIVE"
        );


    };


    document.head.appendChild(script);


})();
"@ | Out-File $jsFile -Encoding UTF8



Write-Host "Frontend Sentry creado"



# ----------------------------------------------------------
# HOOKS.PY
# ----------------------------------------------------------

Write-Host ""
Write-Host "[3] Actualizando hooks.py"


$hooks = ".\nexora_app\nexora\hooks.py"

$content = Get-Content $hooks -Raw


if($content -notmatch "nexora_sentry.js")
{

$content =
$content.Replace(
'app_include_js = [',
'app_include_js = [
	"/assets/nexora/js/nexora_sentry.js",'
)

Set-Content $hooks $content -Encoding UTF8

Write-Host "hooks.py actualizado"

}
else
{
Write-Host "hooks.py ya estaba configurado"
}



# ----------------------------------------------------------
# GITIGNORE
# ----------------------------------------------------------

Write-Host ""
Write-Host "[4] Protegiendo archivos"


Add-Content .gitignore "venv/"
Add-Content .gitignore ".env.sentry"
Add-Content .gitignore "__pycache__/"
Add-Content .gitignore "*.pyc"



# ----------------------------------------------------------
# PRUEBA
# ----------------------------------------------------------

Write-Host ""
Write-Host "[5] Prueba Sentry"


python -c "import sentry_sdk; sentry_sdk.init('$DSN'); sentry_sdk.capture_message('NEXORA FINAL SENTRY TEST')"



# ----------------------------------------------------------
# GIT
# ----------------------------------------------------------

Write-Host ""
Write-Host "[6] Git Commit"


git add .


git commit -m "Complete Sentry monitoring integration frontend backend Nexora"



Write-Host ""
Write-Host "[7] Push GitHub"


git push origin main



Write-Host ""
Write-Host "======================================"
Write-Host " NEXORA SENTRY COMPLETADO"
Write-Host "======================================"

git status