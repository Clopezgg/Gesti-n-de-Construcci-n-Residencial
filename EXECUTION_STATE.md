# NEXORA — Estado de ejecución

- Última actualización: 2026-07-22
- Repositorio: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama técnica única: `nexora-reconstruccion`
- HEAD inicial de `main`: `73c9dadfb81f543e53f45887448fdecbee081850`
- HEAD actual de `main` verificado: `73c9dadfb81f543e53f45887448fdecbee081850`
- HEAD de código runtime previo a esta actualización: `a4ca4b030078840eeb43d513ccdfaa4fb3a2413f`
- Pull Request único: `#11` — `feat(nexora): establish application and canonical financial foundation`
- Estado del Pull Request: **ABIERTO Y SIN FUSIONAR**
- Producción modificada: **NO**
- Rama `main` modificada: **NO**
- Migración histórica: **NO**

## Recuperación y entorno

- La clonación HTTPS local falló por DNS: `Could not resolve host: github.com`.
- GitHub Actions recupera correctamente la rama y ejecuta MariaDB 10.6 en runners aislados.
- No se reconstruyó desde `main`, no se reescribió historia y no se usó `force push`.
- El espacio local `/mnt/data/nexora-block3` contiene únicamente una reconstrucción de trabajo para pruebas determinísticas del Bloque 3; GitHub continúa siendo la fuente remota canónica.

## Pull Request y controles aprobados

PR: `https://github.com/Clopezgg/Gesti-n-de-Construcci-n-Residencial/pull/11`

- `Semantic Commits` — run `29971792002`, job `89095167020` — **APROBADO**.
- `Documentation Required` — run `29971792023`, job `89095166874` — **APROBADO**.
- `Linters` — run `29972703622`:
  - Semgrep job `89097929969` — **APROBADO**;
  - pre-commit job `89097929978` — **APROBADO**.
- `NEXORA app` — run `29972703634`:
  - contrato job `89097929904` — **APROBADO**;
  - instalación/rollback job `89097929946` — **APROBADO**;
  - instalación, migración, fixtures, workspace, roles, convivencia, desinstalación y reinstalación verificadas en MariaDB real.
- `NEXORA financial invariants` — run `29972703658`:
  - infraestructura, instalación y rollback — **APROBADOS**;
  - suite financiera falló porque las pruebas usaban `project_name` como clave Link en vez del `name` canónico generado por ERPNext.
- Commit `a4ca4b030078840eeb43d513ccdfaa4fb3a2413f` corrige la suite y el probe concurrente para conservar el nombre canónico devuelto por ERPNext.
- Este commit humano activa la certificación del PR sobre el árbol corregido.

## Bloques

### Bloque 0 — Gobierno técnico ejecutable

**TERMINADO Y PUBLICADO**

- Baseline concisa, 166 requisitos, propietarios, máquinas, controles, decisiones y validador reproducible.
- Commit principal: `2814acfc655cfbb470e96614cbbc06651023649a`.

### Bloque 1 — Aplicación Frappe NEXORA

**TERMINADO Y VALIDADO EN SHA `666dbb8b8ad9543235b3e423e72a245e8b9f911f`; RECONFIRMACIÓN DEL SHA ACTUAL EN CURSO**

- Aplicación separada, hooks, fixtures, roles, workspace, identidad y assets.
- Instalación, migración, convivencia, desinstalación, reinstalación y rollback aprobados en MariaDB real.
- Run `29972703634`; job runtime `89097929946`.

### Bloque 2 — Núcleo financiero base

**PARCIAL Y PUBLICADO; CERTIFICACIÓN FINAL EN CURSO**

Terminado en código:

- DocTypes canónicos, secuencia de 12 dígitos, fuentes, efectos, asignaciones, compromisos, idempotencia y auditoría;
- vista previa y ejecución compartiendo reglas;
- multifuente, sobregiro, compromiso, liberación, devolución y reclasificación;
- locks, savepoint, rollback, permisos server-side y orquestador obligatorio;
- interfaz mínima real.

Pendiente:

- aprobar la suite Frappe/MariaDB y el probe concurrente sobre el mismo SHA actual;
- registrar run IDs, artefactos y digest final.

## Correcciones runtime relevantes

1. `b7e9b49402f75f1217aa5728aa204752f5a2fcb2` — registro idempotente de `apps.txt`.
2. `83474a04e0e598b1f9f18e8425abc4f07fa21336` — formato exacto de permisos.
3. `666dbb8b8ad9543235b3e423e72a245e8b9f911f` — verificación compatible con salida versionada de `bench list-apps`.
4. `d13e64b725a7533badfa01f924712006b22058b5` — fixture explícito de proyecto.
5. `a4ca4b030078840eeb43d513ccdfaa4fb3a2413f` — uso del nombre canónico ERPNext en suite y concurrencia.
6. Este commit — activación humana del ciclo corregido.

## Siguiente acción exacta

1. Revisar los nuevos runs de `NEXORA app` y `NEXORA financial invariants` sin polling indefinido.
2. Descargar y registrar sus artefactos.
3. Certificar Bloques 1 y 2 únicamente si todos los pasos obligatorios aprueban sobre el mismo SHA.
4. Publicar inmediatamente el Bloque 3 ya validado localmente: catálogos/modelos, kernel+interfaz y pruebas runtime.
