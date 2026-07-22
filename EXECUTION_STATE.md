# NEXORA — Estado de ejecución

- Última actualización: 2026-07-22
- Repositorio: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama: `nexora-reconstruccion`
- HEAD inicial de `main`: `73c9dadfb81f543e53f45887448fdecbee081850`
- Producción modificada: **NO**
- Migración histórica: **NO**
- Rama `main` modificada: **NO**

## Bloques y commits

- Bloque 0: **TERMINADO Y PUBLICADO** — `2814acfc655cfbb470e96614cbbc06651023649a`
- Bloque 1: **TERMINADO Y PUBLICADO** — `4335c3aaa9bb3f629d2d3198e3309b5d95b86c56`
- Bloque 2 / modelos: **TERMINADO Y PUBLICADO** — `fc60faf678a01c6aac0e5224e45f552352b0b1e6`
- Bloque 2 / servicio multifuente: **TERMINADO Y PUBLICADO** — `64c3467d173983d4ed77fef39fcbb0d2f6f3eb16`
- Bloque 2 / pruebas MariaDB y rollback: **PUBLICACIÓN EN ESTE COMMIT** — `SELF`

## Evidencia local previa al commit de pruebas

- `python scripts/validate_nexora_governance.py`: aprobado.
- `python scripts/validate_nexora_app.py`: aprobado.
- `python scripts/validate_nexora_financial_models.py`: aprobado.
- 17 pruebas del motor financiero puro: aprobadas.
- 16 pruebas contractuales de app, modelos, servicios e interfaz: aprobadas.
- `node --check` de `nexora-finance.js`: aprobado.
- `python -m compileall`: aprobado.

## Evidencia remota exigida por este commit

Workflow `NEXORA financial invariants` sobre MariaDB 10.6:

- instalación limpia y migración;
- ocho pruebas Frappe/MariaDB;
- concurrencia real con dos conexiones;
- rollback completo por falla inyectada después de la segunda asignación;
- desinstalación y reinstalación;
- runtime smoke de ConstruControl sin eliminación ni dependencia desde NEXORA.

## Requisitos propietarios materializados por Bloques 0–2

`NXR-GOV-0001` a `NXR-GOV-0011`, `NXR-INF-0001`, `NXR-INF-0006`, `NXR-INF-0007`, `NXR-INF-0009`, `NXR-LCO-0002`, `NXR-LCO-0005`, `NXR-LCO-0006`, `NXR-LCO-0008`, `NXR-LCO-0009`, `NXR-DOC-0001`, `NXR-FND-0001` a `NXR-FND-0020` dentro del alcance financiero base autorizado.

## Siguiente acción exacta

Bloque 3: Libro Central completo, clasificación económica, centros de costo, tipos operativos y efectos analíticos, partiendo del kernel transaccional publicado.
