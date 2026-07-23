# NEXORA 0.1 — Staging reproducible

## Alcance

Este procedimiento levanta exclusivamente los Bloques 0–3 de NEXORA sobre un sitio limpio de staging, test o localhost. No modifica `main`, no fusiona el PR, no toca producción y no migra registros históricos.

## Fuente exacta

- Repositorio: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama: `nexora-reconstruccion`
- Pull Request: `#11`
- Aplicación Frappe: `nexora_app/`
- Script permanente: `scripts/nexora_staging_01.sh`

Antes de levantar el sitio, confirme que el checkout está limpio y que `git rev-parse HEAD` coincide con el SHA que se desea certificar.

## Requisitos

- Ubuntu compatible con el instalador de pruebas del repositorio;
- MariaDB 10.6;
- Node.js 18;
- Python 3.11;
- acceso a las dependencias necesarias para crear un bench Frappe/ERPNext v15;
- un nombre de sitio que contenga `staging`, `test` o termine en `.localhost`.

El script reutiliza un bench existente. Si no existe, ejecuta `.github/helper/install.sh`, el mismo instalador usado por los workflows permanentes de validación.

## Instalación y carga demostrativa

Desde la raíz del checkout:

```bash
export NEXORA_REPO_DIR="$PWD"
export NEXORA_BENCH_DIR="$HOME/frappe-bench"
export NEXORA_SITE="test_site"
export NEXORA_ADMIN_PASSWORD="CAMBIAR-EN-STAGING"

bash scripts/nexora_staging_01.sh bootstrap
```

El comando:

1. rechaza nombres de sitio que no sean staging/test/local;
2. crea o reutiliza el bench;
3. enlaza e instala el paquete `nexora`;
4. registra la aplicación en `sites/apps.txt`;
5. instala NEXORA si todavía no está instalada;
6. ejecuta `bench migrate`;
7. activa `nexora_staging=1` en la configuración del sitio;
8. construye assets;
9. carga datos demostrativos idempotentes y no históricos;
10. ejecuta la verificación de salud NEXORA.

## Datos demostrativos

La carga crea únicamente información marcada como demostrativa:

- dos proyectos NEXORA 0.1;
- tres fuentes de fondos;
- una salida a Cuenta Máxima distribuida entre dos fuentes;
- un anticipo con responsable y vencimiento;
- una transferencia interna entre proyectos;
- usuarios de prueba con roles NEXORA.

Las claves de idempotencia son fijas. Repetir la carga no debe duplicar fuentes ni operaciones.

## Certificación

```bash
export NEXORA_REPO_DIR="$PWD"
export NEXORA_BENCH_DIR="$HOME/frappe-bench"
export NEXORA_SITE="test_site"

bash scripts/nexora_staging_01.sh verify
```

La verificación ejecuta sobre el mismo checkout y sitio:

- gobierno NEXORA;
- contrato de aplicación e imports locales;
- modelos financieros;
- pruebas contractuales;
- núcleos financiero, Libro Central y reglas de referencias;
- sintaxis JavaScript y compilación Python;
- migración;
- instalación, fixtures, workspace, roles y coexistencia;
- invariantes financieras MariaDB;
- invariantes del Libro Central;
- concurrencia con conexiones independientes;
- verificación de salud y datos demostrativos.

El Bloque 3 solo puede declararse certificado cuando `NEXORA app` y `NEXORA financial invariants` estén verdes sobre el mismo SHA.

## Servidor y acceso

```bash
export NEXORA_BENCH_DIR="$HOME/frappe-bench"
export NEXORA_SITE="test_site"

bash scripts/nexora_staging_01.sh serve
```

Con el bench de desarrollo, el acceso habitual es:

```text
http://127.0.0.1:8000
```

Después del login, abra el workspace **NEXORA** o la ruta:

```text
/app/nexora-finance
```

## Evidencia mínima

Conserve junto al SHA certificado:

- salida completa de `bootstrap` y `verify`;
- `bench --site "$NEXORA_SITE" list-apps`;
- JSON de `bench --site "$NEXORA_SITE" execute nexora.staging.assert_staging_health`;
- IDs de runs, jobs, artefactos y digests de los workflows permanentes;
- capturas de login, workspace, Núcleo de Fondos, selección multifuente y Libro Central.

## Rollback de staging

Antes de eliminar un sitio de staging:

```bash
cd "$NEXORA_BENCH_DIR"
bench --site "$NEXORA_SITE" backup --with-files
```

La aplicación bloquea una desinstalación destructiva cuando existen operaciones. En un staging con datos demostrativos, el rollback seguro es conservar el backup y eliminar el sitio completo mediante el procedimiento administrativo del bench. No use este procedimiento contra producción ni contra un sitio con registros reales.
