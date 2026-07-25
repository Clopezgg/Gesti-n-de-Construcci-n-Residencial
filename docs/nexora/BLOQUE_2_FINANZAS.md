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

## Convención

- Un efecto `Funds` positivo aumenta fondos; uno negativo los reduce.
- Un efecto `Reserved` positivo reserva; uno negativo libera o consume reserva.
- Disponible = fondos − reservado.
- La ejecución de compromiso reduce fondos y reserva por el mismo importe; el disponible no se consume dos veces.
- Reclasificar no crea efecto `Funds`.
- Solo `Real Return` con evidencia genera un efecto positivo que restaura fondos.

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
- pruebas Frappe/MariaDB para fuentes, conversión, multifuente, sobregiro, rollback, compromisos, idempotencia, permisos, devolución, reclasificación y secuencia;
- probe con dos conexiones independientes sobre la misma fuente;
- instalación, desinstalación, reinstalación y runtime smoke de convivencia con ConstruControl.

La aprobación definitiva de las pruebas dependientes de MariaDB se registra solo con el SHA del commit y el resultado verificable del workflow `NEXORA financial invariants`.
