# NEXORA — Consola operativa, fechas documentales y cuentas frecuentes

## Requisitos trazables

- `NXR-OPR-20260728-01`: **IMPLEMENTADO Y VALIDADO**. Ingresos, gastos, anulaciones y correcciones aceptan una fecha documental elegida por el usuario, separada de la fecha real de creación y auditoría.
- `NXR-OPR-20260728-02`: **IMPLEMENTADO Y VALIDADO**. Las cuentas frecuentes son reutilizables y el primer registro ya no trata texto libre como una cuenta existente.
- `NXR-OPR-20260728-03`: **IMPLEMENTADO Y VALIDADO**. La consola diaria reconoce los códigos numéricos `101`, `102`, `303`, `304` y `501`.
- `NXR-LGR-20260728-01`: **IMPLEMENTADO Y VALIDADO**. El Libro Central operativo muestra día, fecha documental, documento, código, movimiento, contraparte, institución, cuenta enmascarada, moneda, importe y estado.
- `NXR-UX-20260728-01`: **IMPLEMENTADO Y VALIDADO**. Actividad reciente se limita a tres movimientos y ofrece **Ver más actividad**.
- `NXR-LGR-20260728-02`: **IMPLEMENTADO Y VALIDADO**. Los códigos correctivos quedan definidos sin borrado físico.
- `NXR-OPR-20260728-04`: **IMPLEMENTADO Y VALIDADO**. La selección de una cuenta existente y la creación de una cuenta nueva son modos explícitos y mutuamente excluyentes.
- `NXR-CAT-20260728-01`: **IMPLEMENTADO Y VALIDADO**. Banco o remesadora utiliza el catálogo `Bank`, no texto libre.
- `NXR-UX-20260728-02`: **IMPLEMENTADO Y VALIDADO**. La consola utiliza una estructura transaccional cabecera–líneas–detalle con identidad NEXORA.
- `NXR-VAL-20260728-01`: **IMPLEMENTADO Y VALIDADO**. La interfaz indica los campos bloqueantes y la razón por la que **Contabilizar** permanece deshabilitado.

## Regla operativa de códigos

| Código | Presentación | Implementación canónica | Efecto |
|---|---|---|---|
| `101` | Entrada de saldo | `NXR Fund Source` + `NXR Operation` de ingreso | incrementa una fuente independiente |
| `102` | Salida de saldo / gasto | perfil canónico `CONSTRUCTION_PAYMENT` | consume fuentes y registra clasificación económica |
| `303` | Anulación financiera | cancelación segura del ingreso o `REVERSAL_NO_CASH` | compensa el documento original |
| `304` | Corrección documental | `DOCUMENT_SUBSTITUTION` | conserva el importe financiero y sustituye evidencia o documento |
| `501` | Cancelación total | cancelación segura del ingreso o reversión total | compensa completamente el efecto todavía reversible |

Los códigos numéricos son una capa de operación visible. Los perfiles financieros existentes continúan siendo el motor interno para conservar saldos, efectos, permisos, idempotencia y auditoría.

## Fechas y auditoría

1. **Fecha del documento:** seleccionada por el usuario y usada para el período financiero.
2. **Fecha real de registro:** asignada por Frappe en `creation` y no editable.
3. La fecha documental puede ser histórica.
4. No se acepta una fecha futura.
5. Una corrección, anulación o cancelación no puede fecharse antes de su documento original.
6. Un mes con `NXR Monthly Close` aprobado bloquea nuevos movimientos para ese proyecto y período.
7. La fecha y el proyecto se validan nuevamente en servidor.

## Cuentas frecuentes

El DocType `NXR Financial Account` conserva:

- nombre operativo;
- proyecto opcional;
- uso como origen, destino o ambos;
- remitente o titular;
- banco o remesadora;
- cuenta;
- moneda;
- canal habitual;
- estado y cuenta predeterminada;
- huella única para evitar duplicados.

La creación y lectura de valores completos exige rol operativo financiero. El Libro Central y el dashboard muestran únicamente una cuenta enmascarada. No existe creación directa desde el formulario del DocType; la creación se realiza mediante el servicio financiero auditado.

## Defecto confirmado y corrección

### Comportamiento anterior

1. `financial_account` era un `Autocomplete` que aceptaba texto libre.
2. Un texto no vacío se enviaba como si fuera el nombre interno de un `NXR Financial Account`.
3. El servidor intentaba abrir ese documento antes de evaluar la creación de una cuenta nueva.
4. La casilla **Guardar como cuenta frecuente** solo mostraba `account_name`; no limpiaba ni invalidaba el texto anterior.
5. El flujo fallaba con una cuenta inexistente y nunca alcanzaba la contabilización.

### Comportamiento corregido

La consola separa tres modos:

- `Existing`: requiere una cuenta realmente existente y autorizada para el proyecto;
- `New`: ignora cualquier texto residual de `financial_account`, valida los datos y crea la cuenta en la misma transacción;
- `Manual`: usa los datos solo para el ingreso y no crea una cuenta frecuente.

El backend conserva compatibilidad con el flujo anterior: cuando `account_mode` no existe, `save_financial_account=1` se interpreta como `New`.

## Catálogos y campos

- **Banco o remesadora:** enlace al DocType `Bank`.
- **Moneda:** enlace a `Currency`.
- **Proyecto:** enlace a `Project`.
- **Categoría económica:** enlace a `NXR Economic Category`.
- **Centro de costo:** enlace a `Cost Center`.
- **Contratista o proveedor:** enlace a `NXR Entity`.
- **Documento original:** enlace filtrado a `NXR Operation`.

Efectivo oculta banco, cuenta y referencia bancaria. Remesa, depósito y transferencia los exigen.

## Arquitectura de interfaz

La referencia funcional de captura se adopta como patrón general, sin copiar marca, activos o elementos propietarios:

1. cabecera con pestañas **General** e **Info. documento**;
2. tabla central con una línea financiera activa;
3. detalle inferior por pestañas **Cuenta**, **Importe**, **Clasificación**, **Fondos** y **Evidencia**;
4. vista previa verificable;
5. acción de contabilización bloqueada hasta que exista una vista previa vigente;
6. Libro Central debajo de la transacción.

En escritorio se conserva una disposición compacta. En iPhone y PWA los campos se apilan y las pestañas mantienen desplazamiento horizontal.

## Validaciones visibles

Antes de llamar al servidor, la interfaz comprueba:

- código, fecha y proyecto;
- modo de cuenta;
- existencia real de la cuenta seleccionada;
- nombre de la cuenta nueva;
- canal, moneda, importe, tasa y remitente;
- banco, cuenta y referencia cuando corresponda;
- categoría, beneficiario, medio de pago y asignaciones en gastos;
- documento original y motivo mínimo en correcciones.

Los errores aparecen en un resumen y los campos correspondientes quedan señalados. El servidor vuelve a ejecutar todas las validaciones canónicas.

## Efectos financieros y auditoría

- `101` incrementa saldo mediante efecto `Received`.
- `102` consume asignaciones y conserva efectos de costo y presupuesto.
- `303` crea compensación financiera contra el original.
- `304` crea sustitución documental con importe cero.
- `501` crea compensación total de la porción reversible.
- Ninguna operación contabilizada se elimina físicamente.
- La referencia original, fecha documental, `creation`, usuario, idempotencia y huellas permanecen auditables.
- El modo de cuenta y el nombre de una cuenta nueva forman parte de la huella de vista previa.

## Permisos

- `101` y cuentas frecuentes: Operador financiero, Gerente financiero o Administrador.
- `102`: Operador financiero, Gerente financiero o Administrador.
- `303`, `304` y `501`: Gerente financiero o Administrador.
- Libro Central: roles NEXORA con vista y alcance de proyecto.
- Auditor y visor no reciben números completos mediante los servicios de cuentas.

## Pruebas positivas aprobadas

1. Crear la primera cuenta en modo `New` aunque el navegador conserve texto residual en `financial_account`.
2. Reutilizar una cuenta en modo `Existing`.
3. Registrar un ingreso en modo `Manual` sin crear cuenta.
4. Evitar una segunda cuenta con la misma huella.
5. Mostrar banco o remesadora como enlace al catálogo `Bank`.
6. Renderizar cabecera, línea y detalle.
7. Instalar, migrar, desinstalar, reinstalar y sembrar NEXORA de forma idempotente.
8. Validar escritorio, iPhone y PWA reales.

## Pruebas negativas aprobadas

1. Rechazar una cuenta desconocida en modo `Existing` con mensaje accionable.
2. Rechazar modo `Existing` sin selección.
3. Rechazar modo `New` sin nombre.
4. Rechazar fecha futura o período cerrado.
5. Rechazar remesa, depósito o transferencia sin institución, cuenta o referencia.
6. Rechazar ejecución sin vista previa vigente.
7. Rechazar una cuenta perteneciente a otro proyecto.
8. Preservar operaciones contabilizadas sin borrado físico.

## Evidencia histórica publicada

- PR original fusionado: `#26`.
- SHA funcional original: `b23d9b902191d5693e0841b39ba550ce7cb82d49`.
- HEAD original certificado: `c0b9f9a06f8f9e3d4fc9e9b943abe5615b9c0755`.
- Commit original de fusión: `2e87a0b0ef967efccc3ee0969c095af873a32136`.
- La validación automatizada original no cubrió el texto residual del `Autocomplete` ni la fidelidad cabecera–líneas–detalle.

## Evidencia de corrección publicada

- Rama fusionada: `fix/nexora-financial-account-entry-ui`.
- PR fusionado: `#27`.
- Base verificada: `558c5fef779acdc55659cc44ea5c99dbdfd6124f`.
- SHA funcional probado: `d4b95dd2b9d86c67215a196c8f791a02f5d202ef`.
- HEAD final certificado del PR: `862e676089e4efc67e6e97dbcef36545aee43fbb`.
- Commit de fusión en `main`: `6363ee429ffb9903e2430463e0652a62b82b374e`.
- Linters y Semgrep: run `30379176902`, aprobado.
- Aplicación, contrato, instalación, migración, rollback, reinstalación, escritorio, iPhone y PWA: run `30379177027`, aprobado.
- Invariantes financieras MariaDB: run `30379176679`, aprobado.
- Patch: run `30379176591`, aprobado.
- Gobierno: run `30379177812`, aprobado.
- Documentación: runs `30379177107` y `30379202434`, aprobados.
- Evidencia estática: run `30379177177`, aprobado.
- Control estático de servidor: run `30379176736`, aprobado.
- Control no Python: run `30379176878`, aprobado.
- Validación segura: run `30379177293`, aprobado.
- Commits semánticos: run `30379176607`, aprobado.
- Postgres `30379177412`: omitido por diseño; MariaDB es el motor canónico certificado.

## Criterio de terminado

La corrección existe en backend e interfaz, usa el modelo financiero canónico, valida permisos en servidor, preserva auditoría, maneja errores, incluye pruebas positivas y negativas, está publicada con SHA verificable y fue fusionada en `main` mediante el PR `#27`. Producción y Coolify permanecen fuera de alcance sin autorización expresa, respaldo, rollback y validación posterior.
