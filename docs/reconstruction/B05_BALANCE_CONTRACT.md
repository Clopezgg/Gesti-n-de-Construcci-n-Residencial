# Bloque 5 — Contrato de saldos FI01

Este avance establece una sola regla para reconocer efectivo y calcular saldos:

- `pending` y `held` no se reconocen como efectivo disponible;
- `received` sí se reconoce, salvo conciliación `rejected`;
- `reconciled` fuerza estado `received`;
- `rejected` fuerza estado `cancelled`;
- disponible = recibido − pagado;
- proyectado = recibido − pagado − pendiente;
- una fuente no puede reducirse, retenerse, rechazarse o cancelarse cuando eso deje gastos pagados o comprometidos sin respaldo.

La implementación se verifica mediante 129 pruebas standalone y se integra en la validación de fuentes, el recálculo por gastos vinculados y la autorización de nuevos gastos FI02.
