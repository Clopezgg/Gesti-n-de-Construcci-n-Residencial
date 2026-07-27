# NEXORA — Bloque 2: núcleo financiero base

## Alcance publicado

- Secuencia global de 12 dígitos respaldada por `BIGINT AUTO_INCREMENT` InnoDB.
- Fuentes con saldo individual derivado exclusivamente de `NXR Operation Effect`.
- Operaciones, efectos, asignaciones e idempotencia en una sola transacción MariaDB.
- Asignación multifuente, reservas, ejecución y liberación de compromisos.
- Devolución real con evidencia y reclasificación sin restitución de fondos.
- Vista previa del servidor compartiendo el mismo motor de reglas que la ejecución.
- Interfaz mínima funcional `Núcleo de Fondos`, sin botones simulados.
- Cero nuevas escrituras en `CC Material Ledger`.

## API server-side

Todos los métodos persistentes aceptan únicamente POST y vuelven a comprobar permisos:

- `nexora.financial.service.create_fund_source`
- `nexora.financial.service.list_source_balances`
- `nexora.financial.service.preview_financial_operation`
- `nexora.financial.service.execute_financial_operation`
- `nexora.financial.service.create_commitment`
- `nexora.financial.service.execute_commitment`
- `nexora.financial.service.release_commitment`
- `nexora.financial.sources.cancel_fund_source`

## Anulación segura de ingresos

Una fuente de fondos no se elimina físicamente. Para corregir un ingreso capturado por error:

1. abra el registro `NXR Fund Source`;
2. marque **Anular ingreso**;
3. escriba un motivo de al menos 10 caracteres;
4. guarde el documento.

NEXORA permite esta acción únicamente a `System Manager`, `NEXORA Administrator` y `NEXORA Finance Manager`. Antes de anular, bloquea la fuente y comprueba que conserve únicamente su efecto inicial `Received`, sin gastos, reservas, transferencias ni ajustes relacionados.

Cuando la anulación procede, el sistema:

- crea una operación compensatoria ejecutada;
- registra un efecto `Reversed` negativo por el importe íntegro;
- vincula el efecto revertido;
- marca la operación original como `Compensated Total`;
- cambia la fuente a `Cancelled`;
- conserva motivo, responsable, fecha y operación compensatoria;
- registra un evento de auditoría y una clave idempotente.

Si la fuente ya fue utilizada, la interfaz conserva el ingreso y muestra que primero deben revertirse los movimientos vinculados. No se permiten borrados ni cambios silenciosos de saldo.

## Convención

- Un efecto `Funds` positivo aumenta fondos; uno negativo los reduce.
- Un efecto `Reserved` positivo reserva; uno negativo libera o consume reserva.
- Disponible = fondos − reservado.
- La ejecución de compromiso reduce fondos y reserva por el mismo importe; el disponible no se consume dos veces.
- Reclasificar no crea efecto `Funds`.
- Solo `Real Return` con evidencia genera un efecto positivo que restaura fondos.
- La anulación de un ingreso íntegro crea un efecto `Reversed` por el importe negativo exacto.

## Atomicidad

1. validar acción, payload y clave idempotente;
2. crear savepoint;
3. bloquear fuentes ordenadas por nombre con `FOR UPDATE`;
4. recalcular saldos desde efectos canónicos;
5. emitir secuencia;
6. crear Operation, Allocation, Effect, Audit Event y vínculos;
7. devolver resultado sin `commit` parcial;
8. ante cualquier excepción, rollback al savepoint.

## Evidencia automatizada

- 17 pruebas determinísticas del motor puro.
- 16 pruebas contractuales de app, modelos, servicios e interfaz.
- pruebas Frappe/MariaDB para fuentes, conversión, multifuente, sobregiro, rollback, compromisos, idempotencia, permisos, devolución, reclasificación, anulación segura y secuencia;
- probe con dos conexiones independientes sobre la misma fuente;
- instalación, desinstalación, reinstalación y runtime smoke de convivencia con ConstruControl.

La aprobación definitiva de las pruebas dependientes de MariaDB se registra solo con el SHA del commit y el resultado verificable del workflow `NEXORA financial invariants`.
