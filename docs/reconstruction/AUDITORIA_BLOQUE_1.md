# BLOQUE 1 — Auditoría de contexto, ramas, arquitectura y entorno de control

## 1. Alcance y evidencia utilizada

Esta auditoría reconstruye el contrato inicial mediante evidencia recuperable del proyecto y del repositorio. No afirma haber leído transcripciones literales que no estuvieran disponibles.

Fuentes empleadas:

1. Orden definitiva de corrección controlada mediante Pull Request.
2. Contexto recuperable de «Manual de problema confuso» y «Análisis problema manual».
3. Repositorio oficial, historial, Pull Requests, refs, workflows, código, pruebas y artefactos forenses de GitHub.
4. Snapshot de 4,826 archivos rastreados generado por GitHub Actions sobre el PR #9.

## 2. Gobierno Git verificado

| Elemento | Resultado |
|---|---|
| Repositorio | `Clopezgg/Gesti-n-de-Construcci-n-Residencial` |
| Rama predeterminada | `main` |
| SHA base capturado | `1c5718cd91758576e0cfda1c5f560c32d68f8b79` |
| Rama exclusiva | `reconstruccion-definitiva-construcontrol` |
| Pull Request | #9, abierto y DRAFT contra `main` |
| Permisos verificados | admin, maintain, push, pull y triage |
| Tags | ninguno en el snapshot forense |
| Force push | no utilizado |
| Cambios directos de esta ejecución en `main` | ninguno |

`main` avanzó de forma concurrente después de crear la rama. Se registraron los SHAs observados y no se rebasó ni reescribió la rama de trabajo para ocultar ese hecho.

## 3. Ramas existentes y decisión

El snapshot forense recuperó tres refs de rama:

| Rama | Estado auditado | Diferencia relevante | Decisión |
|---|---|---|---|
| `main` | productiva | fuente oficial | no modificar ni fusionar automáticamente |
| `reconstruccion-definitiva-construcontrol` | activa | contiene únicamente evidencia y correcciones de este PR | conservar durante toda la ejecución |
| `consolidation/construcontrol-canonical-20260719` | divergente | 29 commits exclusivos y 113 commits detrás al comparar; cambios exclusivos concentrados en 12 partes de patch y un workflow de aplicación | no hacer merge; tratar cada patch como propuesta y recuperar solo lógica demostrablemente válida |

No se eliminó ninguna rama.

## 4. Pull Requests históricos

- PR #1: fusionado; incorporó correcciones de identidad, catálogo de construcción, workspace de Integraciones y navegación móvil.
- PR #2: cerrado sin fusionar; rama de validación final con marcadores y diagnósticos.
- PR #3 a #6: cerrados sin fusionar; principalmente disparadores documentales o diagnósticos aislados.
- PR #7 y #8: cerrados; las referencias comparadas no presentaron commits exclusivos útiles frente a `main`.
- PR #9: único centro de control de esta reconstrucción.

Las ramas históricas no se fusionan ciegamente. El código ya fusionado se auditará en su ubicación canónica; los marcadores de validación no se consideran implementación.

## 5. Arquitectura y validación base

La fuente actual contiene una aplicación ERPNext/Frappe con módulos ConstruControl, scripts de validación, Docker Compose, scripts Coolify, PWA y pruebas standalone.

Resultados de la línea base ejecutada sobre el árbol exacto publicado:

| Prueba | Resultado |
|---|---|
| Validación del repositorio | 0 errores |
| Contrato de integración | 37 DocTypes funcionales |
| Contrato de arquitectura | 17 módulos, 28 destinos de workspace revisados |
| Contrato de datos | 36 entidades fuente, 34 DocTypes destino, 37 DocTypes runtime |
| Contrato de producto | 31 archivos, 8 páginas y pruebas requeridas presentes |
| Gobierno de workflows | aprobado |
| Pruebas standalone | 96/96 aprobadas |
| Compilación Python | aprobada |
| Sintaxis JavaScript | aprobada |
| Parseo YAML de workflows | aprobado |
| Ruff en archivos Python modificados | aprobado |

Estas pruebas son línea base, no certificación final de los bloques funcionales 2–12.

## 6. Hallazgos críticos corregidos

### B01-GOV-01 — Escritura automática en producción

Cuatro workflows tenían capacidad de ejecutar `git push` directo a `main`, eliminar ramas remotas o ambas acciones:

- `apply-construcontrol-consolidation.yml`
- `construcontrol-branch-cleanup.yml`
- `construcontrol-container-receipt.yml`
- `construcontrol-verification-receipt.yml`

Se transformaron en validaciones de solo lectura que generan artifacts. Ya no fusionan, borran ramas, crean commits ni actualizan `main`.

### B01-CI-01 — Control de documentación apuntando a otro repositorio

El helper consultaba de forma fija `frappe/erpnext`, por lo que un PR válido de este repositorio podía fallar como «no encontrado». Ahora consume el evento real de GitHub y usa `GITHUB_REPOSITORY` como respaldo.

### B01-CI-02 — Formato de commits contradictorio

El check aceptaba únicamente Conventional Commits, mientras la orden de reconstrucción exige `[B01]` a `[B12]`. El validador ahora acepta estrictamente ambos formatos y sigue rechazando mensajes genéricos.

### B01-REG-01 — Prevención de regresión

Se agregó una prueba que escanea los workflows reales y falla ante:

- push directo a `main`;
- eliminación remota de ramas;
- permisos `contents: write` en los workflows ConstruControl controlados.

## 7. Riesgos y pendientes para el siguiente bloque

1. Revisar cada una de las 12 partes de patch de la rama de consolidación contra el código canónico; no aplicar el conjunto completo.
2. Confirmar en GitHub Actions que la batería remota reproduce la validación local.
3. Identificar propietarios únicos de páginas, rutas, menús, workspaces e integraciones.
4. Mantener vigilancia sobre avances concurrentes de `main` y reconciliar únicamente mediante cambios explícitos en el PR.

## 8. Criterio de cierre del Bloque 1

El Bloque 1 se considera técnicamente implementado cuando:

- el commit de gobierno seguro está publicado;
- GitHub Actions confirma los checks corregidos;
- este informe, la matriz y el checkpoint están publicados;
- el PR permanece DRAFT y `main` no recibe cambios de esta ejecución.
