# NEXORA — Plan Maestro operativo

## Propósito

Construir una plataforma única en español para gestión integral de fondos, proyectos y operaciones, utilizable desde iPhone, escritorio y PWA, con trazabilidad financiera y permisos de servidor.

## Baseline

- Documento aprobado para ejecución: PMI-0.4.
- Requisitos canónicos: 166.
- Máquinas de estado: 37.
- Controles comunes: 32.
- Decisiones: DEC-001 a DEC-019.
- Bloques: 0 a 20.
- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`.
- HEAD de `main` al iniciar: `73c9dadfb81f543e53f45887448fdecbee081850`.
- No se migran registros históricos.

## Método de entrega

Cada bloque exige código real, interfaz cuando aplique, permisos server-side, pruebas positivas y negativas, documentación, actualización de `EXECUTION_STATE.md`, commit publicado y SHA verificable.

## Alcance inmediato

- **Bloque 0:** gobierno ejecutable y baseline versionada.
- **Bloque 1:** aplicación Frappe NEXORA instalable y coexistente.
- **Bloque 2:** secuencia, fuentes, operaciones, efectos, asignaciones, compromisos, vista previa, atomicidad e idempotencia.

## Principios financieros no negociables

- Cada remesa conserva saldo individual.
- No existen saldos negativos.
- Una salida puede usar varias fuentes.
- Un compromiso reserva sin ejecutar.
- Ejecutar un compromiso no descuenta dos veces.
- La transferencia interna no infla ingresos.
- Una salida reduce fondos; no toda salida aumenta costo.
- Las correcciones conservan el original y crean documentos compensatorios.
- Solo una devolución real o restitución comprobada restaura disponible.
- Stock Ledger Entry es el único ledger canónico de inventario.

## Evidencia y estado

La matriz operativa enlaza cada requisito con un bloque propietario, máquina, controles, decisiones y criterio de terminado. El validador de gobierno es la puerta mínima de cada commit NEXORA.
