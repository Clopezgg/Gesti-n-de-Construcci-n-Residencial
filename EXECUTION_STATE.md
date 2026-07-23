# NEXORA — Estado de ejecución

- Última actualización: 2026-07-22
- Repositorio: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama técnica única: `nexora-reconstruccion`
- HEAD inicial de `main`: `73c9dadfb81f543e53f45887448fdecbee081850`
- HEAD actual de `main` verificado: `73c9dadfb81f543e53f45887448fdecbee081850`
- HEAD de calidad publicado: `ce53906d89e1017af62c9408fc3c663bcb6533b0`
- Pull Request único: `#11` — `feat(nexora): establish application and canonical financial foundation`
- Estado del Pull Request: **ABIERTO Y SIN FUSIONAR**
- Producción modificada: **NO**
- Rama `main` modificada: **NO**
- Migración histórica: **NO**

## Recuperación del entorno

- El intento de clonación desde el entorno temporal falló por resolución DNS: `Could not resolve host: github.com`.
- GitHub Actions recuperó correctamente el repositorio, la rama y el merge del PR en runners aislados.
- No se reconstruyó desde `main`, no se reescribió historia y no se realizó `force push`.
- El estado remoto y el PR son las fuentes vigentes para esta certificación.

## Pull Request y certificación CI

PR: `https://github.com/Clopezgg/Gesti-n-de-Construcci-n-Residencial/pull/11`

Evidencia acumulada:

- `NEXORA governance` — run `29970782959`, job `89092161765` — **APROBADO**.
- `NEXORA app` — run `29970783011`:
  - job contractual `89092161994` — **APROBADO**;
  - job runtime anterior aún no constituye certificación final porque fue reemplazado por workflows diagnósticos.
- `NEXORA financial invariants` — run `29970782989`:
  - gates estáticos y determinísticos — **APROBADOS**;
  - ejecución runtime reemplazada por el workflow corregido del mismo PR.
- `Linters` — run `29970782965` produjo artefactos exactos de pre-commit y Semgrep.
- Commit `ce53906d89e1017af62c9408fc3c663bcb6533b0` aplicó el árbol formateado exacto, traducciones, SQL seguro, justificaciones test-only y regresión de locking; el workflow temporal se autoeliminó.
- Las ejecuciones creadas automáticamente por ese commit quedaron en `action_required` sin jobs; este commit humano activa nuevamente todos los controles sobre el árbol corregido.

No se clasifica ninguna prueba runtime como aprobada mientras no exista ejecución visible sobre el mismo SHA y sus artefactos.

## Bloques

### Bloque 0 — Gobierno técnico ejecutable

**TERMINADO Y PUBLICADO; REVALIDACIÓN DE PR EN CURSO**

- Baseline concisa en repositorio.
- 166 identificadores conservados con propietario primario.
- Catálogos de máquinas, controles y decisiones.
- Validador reproducible y workflow de gobierno.
- Commit principal: `2814acfc655cfbb470e96614cbbc06651023649a`.

### Bloque 1 — Aplicación Frappe NEXORA

**PARCIAL Y PUBLICADO**

Terminado:

- aplicación Frappe separada dentro del mismo repositorio;
- hooks, fixtures, roles, workspace, identidad y assets;
- instalación y rollback codificados;
- convivencia sin eliminar ConstruControl;
- pruebas contractuales aprobadas en el PR.

Pendiente para terminado y validado:

- instalación, migración, fixtures, workspace, roles y permisos en sitio real;
- desinstalación y reinstalación verificadas;
- convivencia runtime y rollback con evidencia del mismo SHA.

Commit principal: `4335c3aaa9bb3f629d2d3198e3309b5d95b86c56`.

### Bloque 2 — Núcleo financiero base

**PARCIAL Y PUBLICADO**

Terminado:

- DocTypes canónicos de secuencia, fuente, operación, efecto, asignación, compromiso, idempotencia y auditoría;
- numeración global de 12 dígitos;
- motor financiero determinístico;
- vista previa y ejecución con reglas compartidas;
- asignación multifuente, compromisos, devolución real y reclasificación;
- locks estables, savepoint, rollback e idempotencia implementados;
- permisos server-side y escritura obligatoria mediante orquestador NEXORA;
- interfaz mínima conectada a servicios reales;
- 34 pruebas puras/contractuales aprobadas localmente después de la corrección de calidad.

Pendiente para terminado y validado:

- suite Frappe/MariaDB real;
- dos conexiones concurrentes reales;
- rollback real después de la segunda asignación;
- instalación y convivencia verificadas en sitio;
- artefactos y logs CI asociados al SHA probado.

Commits principales: `fc60faf678a01c6aac0e5224e45f552352b0b1e6`, `64c3467d173983d4ed77fef39fcbb0d2f6f3eb16`, `87b3e877b6209dce96524c39b66243478cbe42c8` y `ce53906d89e1017af62c9408fc3c663bcb6533b0`.

## Correcciones de certificación publicadas

1. `ed0b07e7d7456b3292b2865e74cc6eeddec978c5` — `fix(ci): run financial runtime certification on pull requests`
2. `173b9efcc8bfd7e0c1f35fafa0dd4d7b9baf0881` — `fix(ci): expose NEXORA install and rollback phases`
3. `e16897c99d7743c21d0b5e81762ebae7788910c8` — `docs(nexora): record pull request runtime certification state`
4. `ce53906d89e1017af62c9408fc3c663bcb6533b0` — `fix(nexora): satisfy security and repository quality gates`
5. Este commit — `docs(nexora): trigger certified quality gate execution`

## Errores y bloqueos actuales

- La red del entorno temporal no resuelve `github.com`; no hay checkout Git local persistente.
- Los runners GitHub sí ejecutan el repositorio y MariaDB 10.6.
- Bloques 1 y 2 no se certifican hasta cerrar los fallos y aprobar todos los jobs obligatorios sobre un SHA único.

## Siguiente acción exacta

1. Revisar las ejecuciones asociadas a este SHA sin polling indefinido.
2. Descargar los artefactos de `NEXORA app` y `NEXORA financial invariants`.
3. Corregir cada causa raíz en `nexora-reconstruccion` y mantener abierto el PR #11.
4. Certificar Bloques 1 y 2 únicamente con runs y artefactos aprobados del mismo SHA.
5. Iniciar inmediatamente el **Bloque 3: Libro Central completo y dimensiones analíticas** después de la certificación runtime.
