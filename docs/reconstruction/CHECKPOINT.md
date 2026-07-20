# Checkpoint ConstruControl

- Fecha: 2026-07-19 America/Tegucigalpa
- Pull Request: #9 abierto y en borrador
- Rama única: `reconstruccion-definitiva-construcontrol`
- Base protegida: `main` en `56ad5d9186075b66a89c773bb9c5922329f5687e`
- Bloques certificados: 1, 2, 3 y 4
- Sprint actual: A — finanzas, proyectos y contratos
- Implementación global real: 57%
- Certificación global: Bloques 1–4
- HEAD funcional del Sprint A: `17d7323dd171a08238137c02c37bcbd3683cea6e`

## Bloque 5 — FI01

- Estado: **IMPLEMENTACIÓN COMPLETA — CERTIFICACIÓN PESADA PENDIENTE**.
- Contrato canónico: `funding_amounts`, `normalize_funding_state`, `recognized_funding_amount` y `funding_balances`.
- Consumidores integrados: reportes, cierre semanal y dashboard ejecutivo.
- Evidencia local heredada: 136/136 pruebas standalone aprobadas; compilación y Ruff aprobados en el cierre funcional FI01.
- No se reabrió FI01 porque no apareció un fallo funcional bloqueante de saldo, permisos, doble contabilización o corrupción.

## Bloque 6 — FI02

- Estado: **IMPLEMENTACIÓN COMPLETA — CERTIFICACIÓN PESADA PENDIENTE**.
- Commits: `244c841cdcf961a20ba04b81cae9b77286d8648c`, `7b32f7504f55d428de1834bca6e54744179cf375`.
- Se endurecieron cálculos de subtotal, impuestos, retenciones, descuentos y total.
- Se sincronizaron los estados estándar y profesionales de aprobación.
- Se bloquearon facturas, referencias de pago y cuentas por pagar duplicadas.
- Pagos parciales y completos exigen referencia, fecha y comprobante; los operadores no pueden registrar pagos, anulaciones ni reembolsos.
- Los gastos aprobados quedan protegidos contra cambios financieros o contractuales inconsistentes.
- Solo los gastos aprobados y activos generan una cuenta por pagar; borradores, rechazos, anulaciones y reembolsos archivan la relación sin borrar historial.
- Evidencia dirigida: 6/6 pruebas funcionales aisladas y 8/8 regresiones de contrato aprobadas.

## Bloque 7 — proyectos, fases, presupuestos y contratos

- Estado: **IMPLEMENTACIÓN COMPLETA — CERTIFICACIÓN PESADA PENDIENTE**.
- Commits: `4f68a1da5beef480efb29ee061794d658b4c213b`, `9788c55a2bad1354fb122efd5323c5665641614a`, `17d7323dd171a08238137c02c37bcbd3683cea6e`.
- Fases, fuentes y contratos deben existir y pertenecer al mismo proyecto.
- Un contrato anulado no admite nuevos gastos ni puede conservar gastos aprobados o pagos.
- El valor contractual no puede ser inferior al gasto aprobado ni existir simultáneamente con dos valores divergentes.
- Se eliminó la doble contabilización de gastos contractuales y saldos parciales en los compromisos del proyecto.
- Los contratos sin fase y los gastos sin fase se incluyen en los totales globales sin desaparecer del presupuesto.
- Evidencia dirigida: 3/3 regresiones de compromisos, fases y contratos aprobadas; Python compilado y `tabnanny` aprobado.

## Puerta de certificación A

- Estado: **EN EJECUCIÓN; NO CERTIFICADA TODAVÍA**.
- El primer intento sobre `9788c55a2bad1354fb122efd5323c5665641614a` detectó un contrato estático desactualizado que exigía el nombre anterior del validador FI02.
- La causa fue corregida en `17d7323dd171a08238137c02c37bcbd3683cea6e` sin reducir controles.
- Consulta única del nuevo HEAD: auditoría de rama, documentación, consolidación y commits semánticos aprobados; Linters, validación estática, validación productiva, runtime, contenedor y MariaDB seguían en ejecución.
- La certificación no aumenta hasta obtener evidencia pesada completa del Sprint A.
- No se realizará polling ni se detendrá la implementación esperando GitHub Actions.

## Gobierno preservado

- `main` no fue modificado.
- PR #9 permanece abierto, DRAFT y sin fusionar.
- No se creó otra rama ni otro Pull Request.
- No se usó force push ni se borraron datos, volúmenes, ramas o respaldos.

## Siguiente acción exacta

Continuar con el Sprint B desde el Bloque 8 mientras la Puerta A termina de forma remota. En la próxima puerta real se consultará una sola vez el resultado final del HEAD vigente; cualquier fallo funcional o de seguridad se corregirá agrupadamente.
