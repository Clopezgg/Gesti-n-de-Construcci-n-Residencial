# NEXORA — Bloque 6: Contratistas y Contratos

## Estado del checkpoint

- Rama: `nexora-continuidad-total`.
- PR: `#12`, abierto y sin fusionar.
- Base certificada: Bloque 5 en `e04086e590641ac30ab6dad50b959a307a0393b8`.
- Estado: **EN EJECUCIÓN / NO DEMOSTRADO** hasta completar runtime Frappe/MariaDB y los seis workflows sobre un único SHA.
- Producción, AWS, Coolify y DNS modificados: **NO**.
- Datos históricos migrados: **NO**.

## Requisitos propietarios

| Requisito | Estado del checkpoint | Implementación trazable | Evidencia pendiente |
|---|---|---|---|
| `NXR-CON-0001` | NO DEMOSTRADO | `NXR Contractor Profile` enlazado exclusivamente a `NXR Entity` canónica | instalación, permisos y runtime |
| `NXR-CON-0002` | NO DEMOSTRADO | múltiples `NXR Contract` por perfil y entidad | prueba positiva y consulta |
| `NXR-CON-0003` | NO DEMOSTRADO | modalidades contractuales y líneas separadas | pruebas contractuales y runtime |
| `NXR-CON-0004` | NO DEMOSTRADO | `NXR Contract Amendment`, versión y aplicación no destructiva | adenda positiva, reducción negativa y auditoría |
| `NXR-CON-0005` | NO DEMOSTRADO | anticipo, saldo y amortización mediante Libro Central | desembolso, liquidación parcial e idempotencia |
| `NXR-CON-0006` | NO DEMOSTRADO | estimaciones, hitos y pagos parciales | pago real y conciliación |
| `NXR-CON-0007` | NO DEMOSTRADO | retenciones manuales autorizadas, saldo y devolución | prueba de exceso y devolución |
| `NXR-CON-0008` | NO DEMOSTRADO | estados de terminación, liquidación y cierre | saldos cero y transición terminal |
| `NXR-CON-0009` | NO DEMOSTRADO | lock del contrato y revalidación de saldo | dos conexiones independientes |
| `NXR-CON-0010` | NO DEMOSTRADO | formato Jinja estándar `NEXORA Contract` y acción real de impresión | instalación y renderizado runtime |
| `NXR-CON-0011` | NO DEMOSTRADO | importes y ejecución separados en Labor y Materials | pruebas de conciliación separada |
| `NXR-CON-0012` | NO DEMOSTRADO | evidencia, adendas, estimaciones y movimientos cronológicos | consulta integral y referencias preservadas |

## Modelo de datos

- `NXR Contractor Profile`: clasificación, vigencia, cumplimiento y evidencia de una entidad con rol Contractor.
- `NXR Contract`: alcance original/vigente, fechas, proyecto, centro de costo, fuente, responsable, moneda, montos y saldos.
- `NXR Contract Line`: partidas de mano de obra o materiales sin mezclar saldos.
- `NXR Contract Evidence`: contrato, firmas, aprobación, garantías, pólizas, suspensión y terminación.
- `NXR Contract Amendment`: adenda versionada con ampliación, reducción, plazo, alcance, suspensión, reactivación o terminación.
- `NXR Contract Estimate`: estimación por período y tipo de costo.
- `NXR Contract Transaction`: anticipos, pagos, amortización, retención, multa, deducción, devolución y liquidación.

## Reglas operativas implementadas

1. No existe catálogo paralelo de contratistas; todos derivan de `NXR Entity` y su resolución canónica.
2. El monto original es inmutable; las adendas modifican únicamente importes, plazo, alcance y versión vigentes.
3. Materiales y mano de obra conservan montos y ejecución separados.
4. Anticipos y pagos usan el motor financiero y el Libro Central certificados.
5. Una estimación se revalida bajo lock antes de pagar y no puede exceder el saldo vigente.
6. Retenciones, multas y deducciones son importes manuales autorizados y auditados; no se inventan tasas.
7. La amortización no puede superar el saldo anticipado y referencia la operación de anticipo original.
8. La devolución de retención no puede superar el saldo retenido.
9. La liquidación exige ejecución completa y anticipos/retenciones conciliados.
10. Contratos terminales no se editan; movimientos ejecutados solo admiten corrección referenciada y auditada del Bloque 4.
11. Los saldos ejecutado y pendiente se derivan y persisten en servidor.
12. Suspensión, reactivación y terminación anticipada requieren adenda versionada.
13. La consolidación de entidades conserva la referencia original del contrato y expone el contratista canónico.
14. Toda escritura pasa por servicios, permisos server-side, idempotencia, numeración de 12 dígitos y auditoría.

## Interfaz

La página real `/app/nexora-contracts` permite:

- filtrar por proyecto, contratista y estado;
- crear contratos con líneas de mano de obra y materiales;
- consultar monto vigente, ejecutado, pendiente, pagado, anticipos y retenciones;
- ejecutar transiciones reales mediante servicios server-side;
- abrir el formato imprimible/PDF estándar `NEXORA Contract`;
- acceder a contratos y perfiles desde el workspace NEXORA.

## Pruebas incorporadas

- `test_contract_core.py`: montos, líneas, deducciones, saldos, adendas y estados.
- `test_contract_contract.py`: modelos, servicios, permisos, interfaz, workspace y workflows.
- `test_contract_integration.py`: Frappe/MariaDB, evidencia, finanzas, adendas, anticipos, pagos, retenciones, rollback, liquidación y consolidación.
- `contract_concurrency_probe.py`: dos pagos simultáneos contra un saldo insuficiente para ambos.

## Criterio de terminado

El bloque permanecerá **NO DEMOSTRADO** hasta que instalación, migración, rollback, concurrencia, permisos, consolidación, runtime MariaDB, pre-commit, Semgrep y los seis workflows obligatorios aprueben sobre un único SHA; solo entonces se actualizarán matriz, `EXECUTION_STATE.md` y PR como certificados.
