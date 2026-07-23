# NEXORA — Estado de ejecución

- Última actualización: 2026-07-22
- Repositorio: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama técnica única: `nexora-reconstruccion`
- HEAD inicial de `main`: `73c9dadfb81f543e53f45887448fdecbee081850`
- HEAD actual de `main` verificado: `73c9dadfb81f543e53f45887448fdecbee081850`
- HEAD de rama previo a esta actualización: `173b9efcc8bfd7e0c1f35fafa0dd4d7b9baf0881`
- Pull Request único: `#11` — `feat(nexora): establish application and canonical financial foundation`
- Estado del Pull Request: **ABIERTO Y SIN FUSIONAR**
- Producción modificada: **NO**
- Rama `main` modificada: **NO**
- Migración histórica: **NO**

## Recuperación del entorno

- El intento de clonación desde el entorno temporal falló por resolución DNS: `Could not resolve host: github.com`.
- GitHub Actions sí recuperó el repositorio, la rama y el merge del PR en runners aislados.
- No se reconstruyó desde `main`, no se reescribió historia y no se realizó `force push`.
- El estado remoto y el PR son las fuentes vigentes para esta certificación.

## Pull Request y CI inicial

PR: `https://github.com/Clopezgg/Gesti-n-de-Construcci-n-Residencial/pull/11`

Ejecuciones iniciales asociadas al SHA `02c0b3e3eae315f509ba19899aa16d7d997fd964`:

- `NEXORA governance` — run `29970320879` — **FALLIDO** por incompatibilidad entre el encabezado de HEAD de este archivo y la expresión del validador; corregido en esta actualización.
- `NEXORA app` — run `29970320919`:
  - job contractual `89090760824` — **APROBADO**;
  - job runtime `89090760828` — **FALLIDO** dentro del paso monolítico de instalación/rollback;
  - el workflow se dividió en fases y ahora publica artefactos diagnósticos.
- `NEXORA financial invariants` — **NO INICIADO EN EL PR INICIAL** porque el workflow no tenía disparador `pull_request`; corregido por `ed0b07e7d7456b3292b2865e74cc6eeddec978c5`.
- Los controles heredados del repositorio que fallaron permanecen sujetos a análisis y corrección en la misma rama; no se omiten ni se desactivan.

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
- job contractual del run `29970320919` aprobado.

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
- 33 pruebas puras/contractuales registradas y job contractual del PR aprobado.

Pendiente para terminado y validado:

- suite Frappe/MariaDB real;
- dos conexiones concurrentes reales;
- rollback real después de la segunda asignación;
- instalación y convivencia verificadas en sitio;
- artefactos y logs CI asociados al SHA probado.

Commits principales: `fc60faf678a01c6aac0e5224e45f552352b0b1e6`, `64c3467d173983d4ed77fef39fcbb0d2f6f3eb16` y `87b3e877b6209dce96524c39b66243478cbe42c8`.

## Correcciones de certificación publicadas

1. `ed0b07e7d7456b3292b2865e74cc6eeddec978c5` — `fix(ci): run financial runtime certification on pull requests`
2. `173b9efcc8bfd7e0c1f35fafa0dd4d7b9baf0881` — `fix(ci): expose NEXORA install and rollback phases`
3. Este commit — `docs(nexora): record pull request runtime certification state`

## Errores y bloqueos actuales

- La red del entorno temporal no resuelve `github.com`; no hay checkout local persistente.
- Los runners GitHub sí ejecutan el repositorio y MariaDB 10.6.
- El fallo runtime inicial aún no tiene fase raíz aislada; los workflows corregidos producirán esa evidencia.
- Bloques 1 y 2 no se certifican hasta cerrar los fallos y aprobar todos los jobs obligatorios sobre un SHA único.

## Siguiente acción exacta

1. Revisar una sola vez las nuevas ejecuciones del PR generadas por estos commits.
2. Descargar los artefactos de `NEXORA app` y `NEXORA financial invariants`.
3. Corregir cada causa raíz en `nexora-reconstruccion` y mantener abierto el PR #11.
4. Certificar Bloques 1 y 2 únicamente con runs y artefactos aprobados del mismo SHA.
5. Iniciar inmediatamente el **Bloque 3: Libro Central completo y dimensiones analíticas** después de la certificación runtime.
