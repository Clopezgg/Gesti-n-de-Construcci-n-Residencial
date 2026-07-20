# Checkpoint ConstruControl

- Fecha: 2026-07-19 America/Tegucigalpa
- Pull Request: #9 abierto y en borrador
- Rama única: `reconstruccion-definitiva-construcontrol`
- Base protegida observada al inicio: `main` en `56ad5d9186075b66a89c773bb9c5922329f5687e`
- Bloques certificados: 1, 2, 3 y 4
- Sprint actual: B — operación, avance y analítica
- Implementación global real: 75%
- Certificación global: 33% — Bloques 1–4
- HEAD funcional de Bloque 9: `5dd5379ea04578e4748dfe374562f688908f6ffc`

## Sprint A — FI01, FI02, PR01 y CO01

- Estado: **IMPLEMENTACIÓN COMPLETA — PUERTA A PENDIENTE**.
- No se reabrieron módulos certificados ni funciones del Sprint A porque no apareció un fallo bloqueante de saldo, permisos, doble contabilización o corrupción.
- La certificación pesada se conserva como deuda explícita y se ejecutará una sola vez mediante la Puerta A manual.

## CI por carriles

- Commit: `5b608367c69bd35369db0da76ef7575f5c1061c4`.
- Carril rápido: sintaxis, Ruff, pre-commit, seguridad y pruebas dirigidas continúan en Pull Requests.
- Carril pesado: MariaDB, runtime, contenedor y snapshot forense quedaron exclusivamente bajo `workflow_dispatch` con puerta A, B, C o FINAL.
- No se añadió `continue-on-error`, no se desactivaron controles y no se utilizó `skip-ci`.

## Bloque 8 — MM01, MM02 y MIGO

- Estado: **IMPLEMENTACIÓN COMPLETA — CERTIFICACIÓN DE PUERTA B PENDIENTE**.
- Commits: `6f60d782683c28e5514f8dfbecd4b47c90e5db80`, `40409c46da58028c74abe92a47cdfe56373dfb77`.
- Se consolidaron materiales, categorías, unidades, solicitudes, cotizaciones, proveedor, orden de compra, recepción, bodegas, entradas, consumos, devoluciones, transferencias y ajustes.
- Se bloquearon inventario negativo, salida superior a existencia, referencias duplicadas, transferencias sin destino distinto y ajustes sin justificación/autorización.
- MM02 quedó relacionado con proveedor, bodega, recepción real y gasto FI02 del mismo proyecto.
- Evidencia dirigida: 7/7 pruebas de comportamiento aprobadas; compilación y Ruff aprobados.

## Bloque 9 — QC01 y CL01

- Estado: **IMPLEMENTACIÓN COMPLETA — ESTABILIZACIÓN HISTÓRICA INCLUIDA — CERTIFICACIÓN DE PUERTA B PENDIENTE**.
- Commit funcional: `5dd5379ea04578e4748dfe374562f688908f6ffc`.
- QC01 valida proyecto, fase, responsable, fecha, porcentaje, estados de calidad, incidencias, alertas y regresiones de avance desde backend.
- Las evidencias nuevas deben ser privadas, pertenecer al mismo proyecto/avance, usar un tipo permitido y respetar el límite de tamaño; la eliminación requiere gestión autorizada.
- CL01 calcula saldo inicial, ingresos, gasto reconocido, pagado, pendiente, comprometido, saldo final, saldo proyectado e incidencias.
- Los cierres repetidos reutilizan la misma huella, los borradores pueden recalcularse y los cierres cerrados exigen reapertura autorizada con motivo.
- La migración conserva avances históricos activos como aprobados, mantiene cancelados/rechazados fuera del avance y no inventa estados de calidad desconocidos.
- Evidencia dirigida: 6/6 pruebas funcionales QC01/CL01 y 3/3 pruebas de migración histórica aprobadas; compilación, Ruff y formato aprobados.

## Puertas de certificación

- Puerta A: pendiente; no se ejecutó ni se consultó repetidamente durante la construcción.
- Puerta B: pendiente hasta cerrar BI01 y AU01.
- Puerta C y validación FINAL: pendientes.
- La deuda y su puerta correspondiente están registradas en `docs/reconstruction/DEUDA_VALIDACION.md`.

## Gobierno preservado

- `main` no fue modificado.
- PR #9 permanece abierto, DRAFT y sin fusionar.
- No se creó otra rama ni otro Pull Request.
- No se usó force push ni se borraron datos, volúmenes, ramas o respaldos.

## Siguiente acción exacta

Continuar el Sprint B con el Bloque 10 — BI01 y AU01. Después ejecutar una sola Puerta B conjunta para MM01, MM02, MIGO, QC01, CL01, BI01 y AU01.
