# NEXORA — Diseño de tesorería central de remesas

## Estado y autoridad

Este diseño implementa la decisión explícita del propietario del 22 de agosto de
2026: NEXORA opera con una sola Cuenta Central de Remesas, conserva una fuente
individual por remesa y mantiene `NXR Operation Effect` como único libro de saldos.
No crea un segundo ledger, una aplicación paralela ni migra registros históricos.

## Objetivos verificables

1. Existe exactamente una `NXR Financial Account` administrada por el sistema con
   clave técnica `CENTRAL_REMITTANCE`.
2. Cada remesa nueva enlaza esa cuenta y crea exactamente una `NXR Fund Source`.
3. El saldo consolidado es la suma de los efectos `Funds` de las fuentes enlazadas
   a la cuenta central; el saldo individual se calcula sobre una sola fuente.
4. Compromisos, ejecuciones, correcciones y reversiones siguen escribiendo únicamente
   en `NXR Operation`, `NXR Fund Allocation` y `NXR Operation Effect`.
5. Los cierres de Tesorería Central bloquean cualquier movimiento que afecte una
   fuente de la cuenta central. Los cierres de Proyecto bloquean movimientos
   atribuidos al proyecto. Una operación que cumple ambos criterios debe superar
   ambos controles.
6. El panel no presenta un supuesto saldo de proyecto obtenido filtrando solo por
   `operation.project`. En contexto de proyecto muestra presupuesto disponible,
   comprometido, ejecutado y pendiente; el saldo de caja se identifica como central
   y solo se expone a roles con alcance global.

## Modelo de datos

### `NXR Financial Account`

Se conserva el DocType existente y se amplía, sin crear una cuenta o ledger paralelo:

- `account_role`: `Counterparty` o `Treasury`; los registros existentes conservan
  `Counterparty` por defecto.
- `technical_key`: clave estable, única y de solo lectura; la cuenta central usa
  `CENTRAL_REMITTANCE`.
- `system_managed`: marca de solo lectura que impide desactivar, renombrar, reasignar
  o eliminar una cuenta técnica.

La cuenta central es lógica, no afirma una institución bancaria ni un número de
cuenta inexistente. Sus datos fijos son nombre `Cuenta Central de Remesas`, moneda
`HNL`, canal `Remittance`, alcance global y estado activo. Un patch idempotente la
crea en instalaciones limpias y la reutiliza por `technical_key`.

### `NXR Remittance`

Se añade un enlace de solo lectura `financial_account`. Toda remesa nueva debe apuntar
a la cuenta `CENTRAL_REMITTANCE`. El servicio no ignora una cuenta alternativa: la
rechaza explícitamente. Los registros históricos sin enlace permanecen legibles y no
se backfillean, de acuerdo con la prohibición de migrar históricos.

### `NXR Fund Source`

Continúa siendo el subledger individual: una fuente por remesa. Su enlace `remittance`
permite resolver la cuenta sin duplicar `financial_account`. El proyecto de la fuente
es opcional y no constituye el saldo del proyecto; la atribución analítica vive en los
efectos y asignaciones de cada operación.

### `NXR Operation Effect`

Sigue siendo la única fuente de verdad de fondos y reservas. No se almacena un saldo
mutable en la cuenta o en la remesa. Las consultas consolidadas unen:

`Financial Account → Remittance → Fund Source → Operation Effect`.

## Cálculos

### Consolidado central

- Recibido: efectos `Funds/Received` netos de reversiones.
- Saldo: suma histórica de `Funds` hasta la fecha de corte.
- Comprometido: suma histórica de `Reserved` hasta la fecha de corte.
- Disponible: `Funds - Reserved`.

### Remesa individual

Se aplican las mismas fórmulas a la única fuente enlazada a la remesa. Las operaciones
relacionadas se obtienen por sus allocations/effects, conservando proyecto, centro de
costo, clasificación y documento.

### Proyecto

- Presupuesto aprobado, comprometido, ejecutado y disponible provienen del motor de
  presupuesto canónico.
- Pendiente de pago proviene de compromisos/obligaciones abiertos.
- Gasto y reservas atribuidos provienen de efectos cuyo `project` es el proyecto.
- No se calcula `cash_available_hnl` restando egresos del proyecto a un ingreso central
  que quedó fuera del filtro. El contrato de respuesta identifica explícitamente el
  alcance de cada KPI.

## Períodos cerrados

`NXR Monthly Close` incorpora un alcance explícito:

- `Project`: requiere `project`.
- `Central Treasury`: prohíbe `project` y fotografía únicamente fuentes de la Cuenta
  Central de Remesas.

Una función canónica valida la fecha después de reconocer un replay idempotente y
antes de bloquear/escribir efectos. Se usa desde ingresos, remesas, compromisos,
ejecuciones, pagos, contratos, compras, correcciones, reversiones y anulaciones.
Esto permite que un reintento de una operación ya completada siga devolviendo su
respuesta original aunque el período se haya cerrado posteriormente.

## Seguridad e inmutabilidad

- Las mutaciones validan rol, proyecto real, fuente real y cuenta resuelta en servidor.
- Una fuente central puede financiar un proyecto solo si el actor tiene permiso para
  ejecutar sobre ese proyecto.
- Las consultas estándar de Frappe no pueden eludir el alcance aplicado por los
  servicios NEXORA.
- Cuenta central, remesas, fuentes, allocations, effects, compromisos, secuencias,
  idempotencia y auditoría no admiten eliminación. Las correcciones se representan con
  operaciones compensatorias y referencias al original.
- Los payloads heredados con destinos múltiples o una cuenta alternativa se rechazan;
  no se descartan silenciosamente.

## Precisión monetaria

Los importes usan `money()` únicamente en el resultado monetario. Las tasas usan
`rate()` durante la multiplicación. Esto aplica a remesas, contratos y cualquier otro
flujo en moneda extranjera. Las pruebas usan tasas con más de dos decimales para poder
detectar redondeo prematuro.

## SAP

SAP es un bloque posterior y no altera este modelo. Una prueba fallida cambia la
conexión a estado no activo; el resumen solo considera conectada una configuración con
`status = Active` y `last_test_result = Success`. No se fabrican métricas de conexión
o sincronización.

## Compatibilidad y publicación

- No se migran remesas históricas ni se inventan datos bancarios.
- El patch técnico es idempotente y apto para instalación repetida/rollback de app.
- La implementación se entrega con pruebas positivas, negativas, concurrencia,
  idempotencia, permisos, cierres, precisión y E2E responsive.
- Cada bloque coherente actualiza `EXECUTION_STATE.md`, se commitea, se publica y se
  verifica contra el SHA remoto antes de continuar.
