# Análisis inicial del repositorio — Gestión de Construcción Residencial (NEXORA / ERPNext)

> Informe de solo lectura. No se modificó ningún archivo del repositorio durante este análisis
> (únicamente lectura de archivos, `git status`, `find`, `grep`, `cat`, `gh`).

## 0. Estado real del repositorio

- **Rama actual:** `main` — **HEAD:** `8fc3273d` ("docs(certificacion): registrar el recorrido verde y archivar las ramas #70")
- **`git status`:** limpio, sin cambios pendientes.
- **Relación con origin:** `main` está *up to date* con `origin/main`. Remoto: `github.com/Clopezgg/Gesti-n-de-Construcci-n-Residencial`.
- **PR abierto:** #72 (`claude/nexora-surgical-audit-lsxcuh` → `main`) — todos los checks en verde **excepto** `Frappe real · escritorio · tableta · iPhone · PWA` (falla, 7m1s). Coincide con el ítem #1 abierto en `ROADMAP.md` ("recorrer las ocho operaciones del Capítulo 53").
- **31 ramas remotas** (incluida `main`), 27 de ellas abandonadas (`copilot/*`, `fix/remediation-*`, `codex/*`, `jules-*`, `Clopezgg-patch-*`, `revert-35-*`), tal como lo documenta el propio `ROADMAP.md`.
- **1694 commits** en total en `main`.

## 1. Arquitectura general

Es un **fork de ERPNext/Frappe v15** sobre el que se construyó una capa de negocio propia en **dos generaciones conviviendo**:

- **`erpnext/construcontrol/`** (módulo legado, ~10 DocTypes, 8 páginas, 53 archivos de test): la implementación original "ConstruControl", con su propio subsistema de migración desde Supabase (`erpnext/construcontrol/migration/`, `migration/supabase/*.sql`).
- **`nexora_app/nexora/`** (app Frappe independiente `nexora`, instalada vía `pip install -e apps/nexora`, ~50 DocTypes `nxr_*`, 12 páginas, 92 archivos de test): la reconstrucción vigente. `NEXORA_CONSTITUTION.md` y `AGENTS.md` son explícitos: **ConstruControl debe ser absorbido por NEXORA, no coexistir como producto paralelo** — hoy en el código todavía coexisten ambos.

**Topología de despliegue** (`docker-compose.yml`, `docker-compose.nexora.yml`): patrón estándar de *bench* Frappe — `mariadb` (10.6), `redis-cache`, `redis-queue`, `backend` (gunicorn), `websocket` (Socket.IO), `queue-short`/`queue-long`, `scheduler`, `frontend` (nginx) y un contenedor `backup` dedicado con loop propio. Todo bajo `linux/amd64` fijo, pensado para **AWS EC2 + Coolify** (`docs/deployment/AWS_COOLIFY.md`), con variantes adicionales para Render y Oracle Cloud en `deploy/render/` y `docs/deployment/ORACLE_COOLIFY.md` — **tres objetivos de despliegue documentados en paralelo**, aunque `README.md` fija AWS+Coolify como la única fuente de verdad productiva.

**Frontend:** no hay SPA ni bundler propio (no hay webpack/vite/esbuild config en el repo). La UI se sirve mediante el motor de páginas de Frappe Desk: JS/CSS planos registrados en `nexora_app/nexora/hooks.py` (`app_include_js`/`app_include_css`), más un manifest y service worker propios para PWA (`nexora_app/nexora/public/manifest.json`, `nexora_app/nexora/www/nexora-service-worker.js`).

**Gobernanza documental:** el proyecto se dirige mediante un conjunto de documentos con autoridad jerárquica explícita: `NEXORA_CONSTITUTION.md` (72 capítulos, "máxima autoridad") > `AGENTS.md` (reglas operativas para agentes IA) > `ROADMAP.md` (deuda viva) > `EXECUTION_STATE.md` / `PROJECT_RECONSTRUCTION.md` (histórico). Es un patrón de desarrollo fuertemente asistido por agentes de IA con reglas anti-alucinación y anti-atajos muy explícitas (prohibición de `continue-on-error`, mocks autorreferenciales, `--force`, etc.).

## 2. Tecnologías utilizadas

| Capa | Tecnología |
|---|---|
| Framework base | Frappe `>=15.40.4,<16.0.0` + ERPNext `v15.117.0` |
| Lenguaje backend | Python `>=3.10` |
| Base de datos | MariaDB 10.6 (productiva); Postgres soportado solo en CI (`server-tests-postgres.yml`) |
| Cache / colas | Redis 7 (`redis-cache`, `redis-queue`) |
| Realtime | Socket.IO vía contenedor `websocket` |
| Proxy/estático | nginx (contenedor `frontend`) |
| Frontend | JS vanilla + Frappe Desk, sin bundler propio; PWA (manifest + service worker) |
| Contenedores | Docker (imagen base `frappe/erpnext:${ERPNEXT_VERSION}`), Docker Compose |
| Linters/format | ruff (ámbito `nexora_app/`), eslint + prettier (JS), flake8 (legado erpnext), semgrep (seguridad) |
| Pre-commit | `pre-commit` framework, corre 2 veces en CI para garantizar idempotencia (`linters.yml`) |
| CI/CD | GitHub Actions — **28 workflows** |
| Testing | Runner nativo de `bench` (`FrappeTestCase`/unittest), no pytest — sin `pytest.ini` en el repo |
| Node | v18, Yarn (pero `yarn.lock` de solo 345 bytes — casi todas las deps JS vienen ya resueltas en la imagen base de Frappe) |
| Migración de datos | Scripts SQL de Supabase (`migration/supabase/*.sql`) + importador Python propio |

## 3. Dependencias principales

- **`pyproject.toml` (raíz, heredado de ERPNext estándar):** `pycountry`, `Unidecode`, `barcodenumber`, `rapidfuzz`, `holidays`, `googlemaps`, `plaid-python`, `python-youtube`, `pypng`. Varias de estas (`googlemaps`, `plaid-python`, `python-youtube`) son dependencias del ERPNext genérico sin evidencia de uso por NEXORA/ConstruControl — peso muerto potencial.
- **`nexora_app/pyproject.toml`:** `dependencies = []` — la app NEXORA no declara dependencias Python propias, solo fija el rango de `frappe` y `erpnext` como *bench dependencies*. Diseño limpio: no reinventa librerías.
- **`package.json` (raíz):** una sola dependencia, `onscan.js` (lector de código de barras), sin `devDependencies` — es el `package.json` original de ERPNext, no personalizado.

## 4. Estructura del repositorio (resumen)

```
erpnext/                  ERPNext completo (stock) + módulo construcontrol/ (legado, 10 DocTypes)
nexora_app/nexora/        App Frappe "nexora" (vigente, 50 DocTypes nxr_*, 12 páginas)
deploy/{coolify,nexora,render,ci}/   Scripts de arranque/backup por entorno de despliegue
migration/supabase/       SQL de migración desde el origen histórico (Supabase)
docs/{nexora,architecture,migration,final,reconstruction,validation,deployment}/
                           ~70 documentos .md de auditoría, bloques de trabajo y checklists
scripts/                  38 scripts de validación/certificación (validate_*.py, acceptance_*.py)
tools/nexora_monitor/     Dashboard Node.js/PowerShell de monitoreo de agentes IA (fuera del build de producto)
.github/workflows/        28 workflows (certificación, gates A/B/C/FINAL, secretos, migración de PRs)
```

- **Tamaño total:** ~91 MB (sin `.git`). ~2931 archivos `.py`, ~53.6k líneas solo en `nexora_app` + `erpnext/construcontrol`.
- **Tests:** 92 en `nexora_app`, 53 en `erpnext/construcontrol/tests`, ~499 `test_*.py` en todo el repo (mayoría heredada de ERPNext stock).
- **39 marcadores** `TODO|FIXME|XXX|HACK` en código Python/JS rastreado.

## 5. Riesgos encontrados

1. **Producto duplicado en tránsito.** `erpnext/construcontrol` (legado) y `nexora_app` (vigente) coexisten con DocTypes, páginas y lógica de negocio propias en paralelo — exactamente lo que `NEXORA_CONSTITUTION.md` prohíbe ("no duplicar servicios, DocTypes ni modelos financieros"). La propia constitución reconoce que la migración aún no terminó.
2. **Check de CI en rojo en el PR abierto (#72).** El job `Frappe real · escritorio · tableta · iPhone · PWA` de `nexora-app.yml` falla; es la razón de ser del PR (aún no cerrado) y del ítem #1 del `ROADMAP.md`.
3. **`Patch Test` reportado en rojo sin causa identificada** (`ROADMAP.md`): el log solo devuelve la cola ocupada por el volcado de MariaDB — riesgo de fiabilidad de CI no diagnosticado.
4. **27 ramas remotas abandonadas** sin revisar (posible trabajo útil perdido u obsoleto acumulando ruido en `origin`).
5. **`OPENAI_API_KEY` no configurada para `cr-gpt[bot]`**, según `ROADMAP.md`: el bot comenta en cada PR pidiendo una clave inexistente — ruido operativo constante en revisiones.
6. **`CODEOWNERS` desactualizado**: sigue apuntando a los mantenedores originales de `frappe/erpnext` (`@ruthra-kumar`, `@rohitwaghchaure`, etc.), sin relación con este fork ni con NEXORA — la gobernanza de revisión declarada no coincide con la realidad del proyecto.
7. **Tres estrategias de despliegue documentadas simultáneamente** (AWS/Coolify, Render, Oracle/Coolify) mientras `README.md` fija una sola fuente de verdad productiva — riesgo de configuración divergente entre `docker-compose.yml`, `docker-compose.nexora.yml` y `deploy/render/*`.
8. **Respaldo sin copia externa**, admitido explícitamente en `README.md`: backup y archivo viven en el mismo volumen Coolify; no hay copia cifrada fuera de ese volumen ni prueba periódica de restauración — pérdida total del volumen implica pérdida total de datos.
9. **Dependencias Python posiblemente muertas** (`googlemaps`, `plaid-python`, `python-youtube` en `pyproject.toml` raíz) sin evidencia de uso en `nexora_app`/`construcontrol` — superficie de ataque/mantenimiento innecesaria heredada del ERPNext stock.
10. **`tools/nexora_monitor/`** contiene scripts Node/PowerShell (`final_authorization.ps1`, `run_opencode.ps1`) de orquestación de agentes IA que viven dentro del repositorio de producto — mezcla de tooling de proceso interno con el código del producto.

*(Nada crítico de secretos: el escaneo interno del propio repo — `artifacts/nexora-secrets/report.json`, 554 archivos — reporta `"ok": true` sin hallazgos, y la búsqueda de patrones de claves/tokens en archivos rastreados tampoco encontró coincidencias; ningún `.env` real está trackeado, solo los `.example`.)*

## 6. Mejoras recomendadas

- Cerrar la migración `construcontrol → nexora` de una vez (ya está mandatada por la constitución del propio proyecto) para eliminar la duplicación del punto 1 antes de seguir agregando funcionalidad.
- Diagnosticar la causa raíz de `Patch Test` en vez de dejarlo abierto indefinidamente (Capítulo 51 de la propia constitución exige esto).
- Decidir y ejecutar la limpieza de las 27 ramas abandonadas (revisar contenido antes de borrar, como ya indica `ROADMAP.md`).
- Actualizar `CODEOWNERS` para reflejar la propiedad real del fork.
- Consolidar en una sola estrategia de despliegue documentada como activa y mover las otras a `docs/historical/` si ya no se usan.
- Definir la copia de respaldo externa cifrada que el propio `README.md` señala como pendiente.
- Auditar y podar dependencias Python no usadas en `pyproject.toml` raíz.

## 7. Estado general del proyecto

Repositorio **activo y en operación real** (no un prototipo): CI extenso con 28 workflows, `main` protegida, flujo de PR con múltiples gates de certificación (`gate-a/b/c/final`, `secrets`, `semgrep`, pruebas E2E en escritorio/tableta/iPhone/PWA), y un proceso de trabajo muy disciplinado documentado en `AGENTS.md`/`NEXORA_CONSTITUTION.md`. `main` está actualmente **verde y limpio**. El trabajo en curso (PR #72) está a un solo check de cerrarse. El proyecto se encuentra en una **fase de consolidación**: absorber definitivamente ConstruControl dentro de NEXORA, con deuda técnica y de proceso claramente inventariada por el propio equipo (no oculta), lo cual es una señal positiva de madurez operativa pese al tamaño de la deuda pendiente.
