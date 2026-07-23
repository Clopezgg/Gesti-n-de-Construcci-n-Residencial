# NEXORA — Estado de ejecución

- Última actualización: 2026-07-22
- Repositorio: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama técnica única: `nexora-reconstruccion`
- HEAD inicial de `main`: `73c9dadfb81f543e53f45887448fdecbee081850`
- HEAD actual de `main`: `73c9dadfb81f543e53f45887448fdecbee081850`
- SHA certificado de Bloques 1 y 2: `e0b8d1edccc13346c3429b8ef22d8bbf8173ce91`
- Pull Request único: `#11` — abierto y sin fusionar
- Producción modificada: **NO**
- Migración histórica: **NO**

## Recuperación

- La clonación HTTPS local permanece bloqueada por DNS: `Could not resolve host: github.com`.
- GitHub Actions recuperó y probó la rama en runners aislados con ERPNext/Frappe v15 y MariaDB 10.6.
- No se usó `main` como árbol de trabajo, no se reescribió historia y no se realizó `force push`.
- `/mnt/data/nexora-block3` es una reconstrucción local no canónica usada para validar el siguiente bloque; GitHub es la fuente vigente.

## Certificación runtime — mismo SHA

### NEXORA app

- Workflow: `NEXORA app`
- Run ID: `29973917049`
- SHA: `e0b8d1edccc13346c3429b8ef22d8bbf8173ce91`
- Job contractual: `89101582734` — **APROBADO**
- Job instalación/rollback: `89101582715` — **APROBADO**
- Artefacto: `8550778391`
- Nombre: `nexora-app-e0b8d1edccc13346c3429b8ef22d8bbf8173ce91`
- Digest: `sha256:65d9eec50f163c6c6866d633df5658fee263b3d8d74c99c98481140976cef4e1`

Evidencia aprobada: instalación en sitio limpio, migración, fixtures, workspace, roles, permisos, convivencia con ConstruControl, desinstalación, reinstalación y rollback.

### NEXORA financial invariants

- Workflow: `NEXORA financial invariants`
- Run ID: `29973917014`
- Job MariaDB: `89101582623` — **APROBADO**
- SHA: `e0b8d1edccc13346c3429b8ef22d8bbf8173ce91`
- Artefacto: `8550776607`
- Nombre: `nexora-financial-e0b8d1edccc13346c3429b8ef22d8bbf8173ce91`
- Digest: `sha256:6257913ef2480f1d863d8ec98328a58df2e5ae7bf25dda45de628c41705f6dfa`

Evidencia aprobada:

- DocTypes instalados y migrados;
- secuencia global única de 12 dígitos;
- fuentes HNL y moneda extranjera;
- efectivo sin institución bancaria;
- rechazo de transferencia incompleta;
- salida multifuente L6,000 + L4,000;
- rechazo de asignaciones incorrectas y sobregiro;
- idempotencia y conflicto de payload;
- rollback total después de fallar la segunda asignación;
- compromiso, ejecución y liberación sin doble descuento;
- reclasificación sin devolución;
- devolución real con evidencia;
- permisos server-side;
- prohibición de escrituras canónicas directas;
- auditoría e interfaz conectada;
- concurrencia real con dos conexiones independientes y saldo final serializado.

## Controles de calidad del candidato

- `NEXORA governance` — run `29973917037` — **APROBADO**.
- `Semantic Commits` — run `29973917027` — **APROBADO**.
- `Documentation Required` — run `29973917060` — **APROBADO**.
- Semgrep — run `29973917015`, job `89101582573` — **APROBADO**.
- Pre-commit detectó únicamente formato Ruff en dos expresiones de la corrección de concurrencia; el formato exacto se incorporó al primer commit del Bloque 3 sin alterar la lógica certificada.

## Bloques

### Bloque 0 — TERMINADO Y PUBLICADO

Baseline, 166 requisitos, propietarios, máquinas, controles, decisiones y validador reproducible.

### Bloque 1 — TERMINADO Y VALIDADO

Certificado en SHA `e0b8d1edccc13346c3429b8ef22d8bbf8173ce91`, run `29973917049`.

### Bloque 2 — TERMINADO Y VALIDADO

Certificado en SHA `e0b8d1edccc13346c3429b8ef22d8bbf8173ce91`, run `29973917014`.

### Bloque 3 — PREPARADO Y VALIDADO LOCALMENTE; PUBLICACIÓN INMEDIATA

- 10 DocTypes canónicos;
- 23 tipos oficiales de operación;
- 21 categorías económicas;
- efectos de fondos, reservas, costo, presupuesto, ahorro e inversión;
- Cuenta Máxima, transferencias, otros proyectos, terrenos, propietaria, regalos, donaciones, contribuciones, impuestos, pagos legales, viajes, especiales, anticipos, liquidaciones, reclasificaciones, devoluciones, reversiones y sustituciones;
- 22 pruebas contractuales y 26 pruebas puras aprobadas;
- interfaz mínima real conectada al kernel del Bloque 2;
- sin segundo ledger ni escrituras a `CC Material Ledger`.

## Siguiente acción exacta

Publicar el Bloque 3 en tres commits coherentes, regenerar el inventario estático del repositorio y ejecutar sus controles en el mismo PR #11.
