#!/usr/bin/env bash
# NEXORA — orquestador seguro del reset de un entorno de staging descartable
# (Sección B del runbook: docs/nexora/RUNBOOK_INICIALIZACION_RESET_ENTORNO.md).
#
# Este script NO inventa ningún mecanismo nuevo: encadena, en el orden
# correcto y con las comprobaciones reales que el runbook exige a mano,
# los mismos comandos `bench` ya documentados — conteo previo, respaldo
# verificable, uninstall/install, conteo posterior. Reduce el riesgo real
# de un paso saltado u omitido al transcribir el procedimiento a mano.
#
# Deliberadamente NO cubre el escenario B2 (sitio con registros reales de
# NXR Operation ya creados por el usuario): `before_uninstall()`
# (nexora_app/nexora/install.py) rechaza incondicionalmente la
# desinstalación en ese caso, sin ninguna bandera de "forzar" en todo el
# repositorio — por diseño, no por omisión (ver el propio código real).
# Construir ahí un mecanismo de purga selectiva violaría el principio de
# libro inmutable que protege el resto de NEXORA; requeriría una decisión
# de producto nueva y separada, no algo que este script deba improvisar.
#
# Uso:
#   scripts/nexora_environment_reset.sh --site <site> --confirm
#
# Requiere ejecutarse donde exista un `bench` real ya inicializado — este
# entorno de desarrollo no lo tiene, así que este script se entrega
# verificado sintácticamente (`bash -n`) pero nunca ejecutado contra un
# sitio real desde aquí.

set -euo pipefail

SITE=""
CONFIRMED=0
BACKUP_DIR="${NEXORA_RESET_BACKUP_DIR:-./nexora-reset-backups}"

usage() {
	echo "Uso: $0 --site <site> --confirm" >&2
	echo "  --site <site>   Sitio Frappe real sobre el que operar (obligatorio)." >&2
	echo "  --confirm       Reconocimiento explícito de que esto reinicia el sitio (obligatorio)." >&2
	exit 1
}

while [ $# -gt 0 ]; do
	case "$1" in
	--site)
		SITE="${2:-}"
		shift 2
		;;
	--confirm)
		CONFIRMED=1
		shift
		;;
	*)
		echo "Argumento no reconocido: $1" >&2
		usage
		;;
	esac
done

if [ -z "$SITE" ]; then
	echo "ERROR: falta --site <site>." >&2
	usage
fi

if [ "$CONFIRMED" -ne 1 ]; then
	echo "ERROR: falta --confirm — este script reinicia por completo el sitio '$SITE'." >&2
	echo "No se ejecuta nada sin ese reconocimiento explícito." >&2
	usage
fi

if ! command -v bench >/dev/null 2>&1; then
	echo "ERROR: no se encontró 'bench' en PATH — este script debe correr dentro de un frappe-bench real." >&2
	exit 1
fi

mkdir -p "$BACKUP_DIR"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
PRECOUNT_FILE="$BACKUP_DIR/${SITE}-${TIMESTAMP}-precount.json"
POSTCOUNT_FILE="$BACKUP_DIR/${SITE}-${TIMESTAMP}-postcount.json"

echo "[1/6] Conteo previo real de registros de negocio en '$SITE'..."
bench --site "$SITE" execute nexora.financial.reset_readiness.count_business_records \
	>"$PRECOUNT_FILE"
echo "      Guardado en: $PRECOUNT_FILE"
cat "$PRECOUNT_FILE"

echo "[2/6] Respaldo verificable real (bench backup --with-files)..."
bench --site "$SITE" backup --with-files

echo "      Backup real solicitado a bench — verifique el archivo generado bajo"
echo "      sites/$SITE/private/backups/ antes de continuar (este script no"
echo "      asume su ruta exacta ni su contenido: bench decide el nombre real)."

read -r -p "      ¿Confirma que el respaldo anterior es real y restaurable? [escriba 'si' para continuar] " backup_ack
if [ "$backup_ack" != "si" ]; then
	echo "ABORTADO: respaldo no confirmado. Ningún dato fue tocado." >&2
	exit 1
fi

echo "[3/6] Desinstalando la app NEXORA de '$SITE'..."
echo "      Si el sitio ya tiene NXR Operation reales, 'before_uninstall()'"
echo "      rechazará este paso por diseño (Bloque 159) — eso es correcto,"
echo "      no un fallo de este script. Ver la Sección B2 del runbook."
bench --site "$SITE" uninstall-app nexora

echo "[4/6] Reinstalando la app NEXORA en '$SITE'..."
bench --site "$SITE" install-app nexora

echo "[5/6] Migrando '$SITE'..."
bench --site "$SITE" migrate

echo "[6/6] Conteo posterior real..."
bench --site "$SITE" execute nexora.financial.reset_readiness.count_business_records \
	>"$POSTCOUNT_FILE"
echo "      Guardado en: $POSTCOUNT_FILE"
cat "$POSTCOUNT_FILE"

echo ""
echo "Reset completado. Compare manualmente:"
echo "  Antes:   $PRECOUNT_FILE"
echo "  Después: $POSTCOUNT_FILE"
echo "El sitio debe quedar sin registros transaccionales de negocio."
