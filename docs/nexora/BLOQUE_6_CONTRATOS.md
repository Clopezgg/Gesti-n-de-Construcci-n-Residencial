# NEXORA — Bloque 6: Contratistas y Contratos

## Estado certificado

- Rama: `nexora-continuidad-total`.
- PR: `#12`, abierto y sin fusionar.
- Base certificada: Bloque 5 en `e04086e590641ac30ab6dad50b959a307a0393b8`.
- SHA funcional certificado: `3d2b65792b149d5ad915e7b1aec64423b3b048f0`.
- Estado: **IMPLEMENTADO Y VALIDADO**.
- Producción, AWS, Coolify y DNS modificados: **NO**.
- Datos históricos migrados: **NO**.

## Requisitos certificados

`NXR-CON-0001` a `NXR-CON-0012` quedan **IMPLEMENTADOS Y VALIDADOS** en `3d2b65792b149d5ad915e7b1aec64423b3b048f0` con evidencia de modelos, servicios, interfaz, permisos server-side, pruebas positivas y negativas, runtime Frappe/MariaDB, auditoría, idempotencia, rollback y concurrencia.

| Requisito | Evidencia verificable |
|---|---|
| `NXR-CON-0001` | `NXR Contractor Profile` enlaza exclusivamente una `NXR Entity` canónica; no existe catálogo paralelo de contratistas. |
| `NXR-CON-0002` | Una entidad puede conservar múltiples contratos independientes y consultables. |
| `NXR-CON-0003` | Modalidades y líneas contractuales reales con montos separados por mano de obra y materiales. |
| `NXR-CON-0004` | Adendas versionadas no destructivas; el monto original permanece inmutable y una reducción inválida se rechaza. |
| `NXR-CON-0005` | Anticipo contractual ejecutado en el motor financiero y conciliado mediante amortización referenciada. |
| `NXR-CON-0006` | Estimaciones, hitos y pagos parciales revalidados bajo lock y registrados en el Libro Central. |
| `NXR-CON-0007` | Retenciones manuales autorizadas, auditadas y sin tasas inventadas; devolución excesiva rechazada. |
| `NXR-CON-0008` | Terminación, liquidación y estado terminal con saldos conciliados e inmutabilidad posterior. |
| `NXR-CON-0009` | Dos conexiones independientes intentan pagar contra saldo insuficiente; solo una ejecución prospera. |
| `NXR-CON-0010` | Formato Jinja `NEXORA Contract` instalado en Frappe y acción real de impresión/PDF conectada desde `/app/nexora-contracts`. |
| `NXR-CON-0011` | Mano de obra y materiales conservan importes, ejecución y saldos separados. |
| `NXR-CON-0012` | Evidencias, adendas, estimaciones, movimientos, correcciones y resolución canónica forman un expediente cronológico. |

## Modelo de datos certificado

- `NXR Contractor Profile`: clasificación, vigencia, cumplimiento y evidencia de una entidad con rol Contractor.
- `NXR Contract`: alcance original/vigente, fechas, proyecto, centro de costo, fuente, responsable, moneda, montos y saldos.
- `NXR Contract Line`: partidas de mano de obra o materiales sin mezclar saldos.
- `NXR Contract Evidence`: contrato, firmas, aprobación, garantías, pólizas, suspensión y terminación.
- `NXR Contract Amendment`: adenda versionada con ampliación, reducción, plazo, alcance, suspensión, reactivación o terminación.
- `NXR Contract Estimate`: estimación por período y tipo de costo.
- `NXR Contract Estimate Line`: detalle de ejecución conciliado contra líneas contractuales.
- `NXR Contract Transaction`: anticipos, pagos, amortización, retención, multa, deducción, devolución, corrección y liquidación.

## Reglas operativas certificadas

1. Todos los contratistas derivan de `NXR Entity` y su resolución canónica.
2. El monto original es inmutable; las adendas modifican únicamente valores, plazo, alcance y versión vigentes.
3. Materiales y mano de obra conservan montos y ejecución separados.
4. Anticipos y pagos usan el motor financiero, fuentes y Libro Central certificados.
5. Una estimación se revalida bajo lock antes de pagar y no puede exceder el saldo vigente.
6. Retenciones, multas y deducciones son importes manuales autorizados y auditados; no se inventan tasas.
7. La amortización no puede superar el saldo anticipado y referencia la operación original.
8. La devolución de retención no puede superar el saldo retenido.
9. La liquidación exige ejecución completa y anticipos/retenciones conciliados.
10. Contratos terminales no se editan; correcciones usan documentos referenciados y auditados.
11. Suspensión, reactivación y terminación anticipada requieren adenda versionada.
12. Toda escritura pasa por servicios, permisos server-side, idempotencia, numeración de 12 dígitos y auditoría.

## Interfaz certificada

La página real `/app/nexora-contracts` permite filtrar, crear contratos con líneas, consultar saldos, ejecutar transiciones server-side y abrir el formato imprimible `NEXORA Contract`. El workspace NEXORA expone la página, contratos y perfiles de contratista.

## Pruebas y runtime

- 49 pruebas contractuales estáticas: **APROBADAS**.
- 60 pruebas puras: **APROBADAS**.
- 4 pruebas de integración contractual Frappe/MariaDB: **APROBADAS**.
- instalación, migración limpia, desinstalación, reinstalación y rollback: **APROBADOS**.
- permisos negativos, sobreestimación, adenda inválida, superposición de perfil y devolución excesiva: **RECHAZADOS CORRECTAMENTE**.
- pago con fallo inyectado: **ROLLBACK APROBADO**.
- liquidación terminal e inmutabilidad posterior: **APROBADAS**.
- concurrencia contractual: resultado `paid`/`denied_overpay`, `paid_count=1`: **APROBADA**.
- pre-commit y Semgrep: **APROBADOS**.

## Workflows del SHA funcional

| Workflow | Run ID | Job(s) | Resultado |
|---|---:|---:|---|
| NEXORA governance | `30117634460` | `89562121818` | APROBADO |
| NEXORA app | `30117634489` | `89562121692`, `89562121707` | APROBADO |
| NEXORA financial invariants | `30117634438` | `89562121557` | APROBADO |
| Linters | `30117634559` | `89562121910`, `89562121930` | APROBADO |
| Semantic Commits | `30117634511` | `89562121923` | APROBADO |
| Documentation Required | `30117634482` | `89562121673` | APROBADO |

## Artefactos

| Evidencia | Artefacto | Digest |
|---|---:|---|
| Inventario de gobierno | `8606055472` | `sha256:a39ed33a0dfe6ed98417279ca3c79a051f2d3e92e0543a436c8282e1ad338a66` |
| Aplicación, instalación y rollback | `8606171543` | `sha256:7cf12d367d7c202f135676749cbfa3b2b5f522bd7004edd8508ba6ad285949c8` |
| Runtime financiero, contractual y concurrencia | `8606196349` | `sha256:2321f2c24a751a179b753a8b6e0195333f94ed75b7db350ea0866c12d769f612` |
| Pre-commit / Linters | `8606078373` | `sha256:6d46a2d70286abad49874fabd5ba6fbe65e9f417d2f1bc4b6c25b2a2bc44b8b0` |
| Semgrep | `8606068215` | `sha256:1b745063ae253b92ccd12138c6e42789a85051977969c1ffb9949f330e925c1c` |

## Siguiente bloque

Bloque 7 — Compras y Proveedores. Debe reutilizar `NXR Entity`, `NXR Evidence`, motor financiero, Libro Central, fuentes, categorías, centros de costo, proyectos, idempotencia, auditoría, locks, permisos y secuencias sin arquitectura paralela.
