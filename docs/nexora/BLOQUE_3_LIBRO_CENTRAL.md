# NEXORA — Bloque 3: Libro Central y dimensiones analíticas

## Estado

**PUBLICADO PARA CERTIFICACIÓN RUNTIME.** No debe clasificarse como terminado y validado hasta que los workflows del PR #11 aprueben sobre un mismo SHA y sus artefactos queden registrados en `EXECUTION_STATE.md`.

## Alcance

- Catálogos canónicos `NXR Operation Type` y `NXR Economic Category`.
- Clasificación económica separada del perfil operativo y tipo técnico derivado en servidor.
- Efectos en Fondos, Reservado, Costo, Presupuesto, Ahorro e Inversión.
- División analítica entre centros de costo sin crear un ledger paralelo.
- Cuenta Máxima, ahorro, transferencias internas, otros proyectos, terrenos, depósitos a la propietaria, regalos, donaciones, contribuciones, impuestos, pagos legales, viajes y pagos especiales.
- Anticipos, liquidaciones, reclasificaciones, devoluciones reales, reversiones sin efectivo y sustituciones documentales referenciadas.
- Consulta cronológica del Libro Central e interfaz conectada a servicios reales.

## Ledger canónico único

- Toda persistencia financiera y analítica usa exclusivamente `NXR Operation Effect`.
- No se crea otro ledger y no se escribe `CC Material Ledger`.
- Cada operación conserva número, proyecto, clasificación, centro de costo, referencia original, correlación, solicitante, aprobador y ejecutor.
- Las correcciones derivan sus importes y dimensiones de efectos ejecutados; no aceptan efectos manuales independientes.

## Reclasificación financiera real

- Requiere una operación base ejecutada.
- El servidor calcula el saldo reclasificable del documento original.
- Cada dimensión genera un efecto negativo enlazado al efecto anterior y un efecto positivo en la clasificación nueva.
- El neto por dimensión es cero y no existe movimiento de Fondos ni Reservado.
- El importe no puede superar el saldo todavía reclasificable.
- La idempotencia devuelve el mismo documento; otra clave no puede duplicar ni exceder lo ya reclasificado.

## Devolución real

- Requiere referencia a una salida o ejecución de compromiso ejecutada y evidencia comprobable.
- La restitución usa la misma fuente original o una fuente distinta con relación explícita `related_source`.
- El servidor calcula el saldo recuperable por fuente descontando devoluciones ejecutadas anteriores.
- Se bloquean fuentes repetidas, relaciones inexistentes, importes nulos y devoluciones acumuladas superiores al desembolso.
- Solo una devolución real aprobada incrementa Fondos.

## Reversión sin efectivo

- Requiere una operación base ejecutada y deriva proyecto, centro de costo, clasificación, dimensión e importe desde sus efectos originales.
- Crea únicamente efectos analíticos negativos enlazados mediante `reverses_effect`.
- No restaura Fondos ni Reservado.
- Bloquea doble reversión y cualquier importe superior al saldo reversible.

## Anticipos y liquidaciones

- El desembolso exige beneficiario o responsable, fecha, vencimiento y separación de funciones.
- La liquidación referencia el desembolso ejecutado y conserva su beneficiario, fecha y vencimiento.
- Se registran total entregado, total liquidado y saldo pendiente.
- Las liquidaciones acumuladas no pueden superar el anticipo y la idempotencia impide duplicarlas.
- Liquidar reconoce costo o inversión según la clasificación, pero no consume fondos ni presupuesto por segunda vez.

## Separación de funciones

Solicitante, aprobador y ejecutor deben ser tres usuarios distintos para:

- transferencia interna;
- desembolso de anticipo;
- liquidación de anticipo;
- reclasificación;
- devolución real;
- reversión sin efectivo;
- sustitución documental.

La validación se ejecuta en servidor antes de consultar o bloquear el documento original y vuelve a validarse en el DocType canónico.

## Interfaz

- El usuario selecciona únicamente `NXR Operation Type` y la categoría económica permitida.
- El tipo técnico `operation_type` no se captura manualmente; el catálogo lo deriva y el formulario lo muestra solo como dato de lectura.
- La interfaz selecciona automáticamente el servicio de compromiso o el servicio central.
- Beneficiario, vencimiento, referencia, destino, evidencia, medio de pago y relación de fuente aparecen solo cuando el perfil los requiere.
- La ejecución permanece deshabilitada hasta obtener una vista previa calculada por servidor.

## Evidencia de pruebas incluida

- Pruebas puras para límites, efectos compensatorios, relaciones de fuente, fechas, saldos de anticipo y segregación.
- Pruebas contractuales de modelos, persistencia, ledger único e interfaz derivada por perfil.
- Pruebas Frappe/MariaDB positivas, parciales, idempotentes, duplicadas y excesivas para reclasificación, devolución, reversión, anticipos y sustitución documental.
- Workflow financiero configurado para ejecutar las pruebas puras nuevas y las integraciones MariaDB en el mismo PR.
