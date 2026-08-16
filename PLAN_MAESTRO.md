# NEXORA — Plan Maestro canónico

## Propósito

Conducir NEXORA como producto único para gestión integral de fondos, proyectos y operaciones, en español claro, con Frappe/ERPNext como motor interno y sin identidades, ledgers, dashboards o fuentes de saldo paralelas.

## Fuente de verdad

1. `NEXORA_CONSTITUTION.md` manda sobre cualquier otro documento.
2. `AGENTS.md` define la operación del agente en este repositorio.
3. `EXECUTION_STATE.md` registra la evidencia histórica por bloque y sus límites.
4. `docs/nexora/` contiene antecedentes operativos, auditorías, matrices ampliadas y decisiones.
5. Los tests bajo `nexora_app/nexora/tests/` son evidencia ejecutable, pero no sustituyen pruebas de runtime real cuando el requisito depende de Frappe/MariaDB/navegador/servicio externo.

## Estados permitidos

Toda planificación y todo requisito deben usar solo: `CONFIRMADO`, `PROPUESTO`, `REQUIERE DECISIÓN`, `EXISTENTE Y REUTILIZABLE`, `EXISTENTE PERO DEFECTUOSO`, `OBSOLETO`, `OBSOLETO JUSTIFICADO`, `NO DEMOSTRADO`, `IMPLEMENTADO Y VALIDADO` o `IMPLEMENTADO — ACTIVACIÓN EXTERNA PENDIENTE`.

## Fases únicas

| Fase | Objetivo | Estado | Entregables |
|---|---|---|---|
| Fase 1 | Recuperación del producto principal: NEXORA como inicio, navegación y experiencia principal. | EXISTENTE Y REUTILIZABLE | Dashboard, navegación, páginas, PWA, proyectos, fondos, operaciones, contratos, proveedores, evidencias, cuentas y reportes. |
| Fase 2 | Simplificación operativa: ingresos, remesas, depósitos, gastos, pagos y correcciones con datos conocidos por el usuario. | EXISTENTE Y REUTILIZABLE | Wizards, preview, validaciones, locks, secuencias, permisos, integridad, conciliación y rollback en backend. |
| Fase 3 | Integración y publicación definitiva: recorridos reales, permisos, saldos, errores, persistencia, escritorio, iPhone, PWA, migraciones, seguridad y CI. | NO DEMOSTRADO | Requiere CI completo del SHA publicado, smoke de navegador, instalación/migración/rollback y confirmación de `main`. |

## Reglas de avance

- No iniciar auditorías generales ni reconstrucciones desde cero.
- Conservar o integrar lo existente cuando sea funcional y coherente.
- Corregir causa raíz cuando algo sea defectuoso.
- Retirar solo lo obsoleto con justificación y sin pérdida de datos, permisos o relaciones.
- No crear aplicaciones, dashboards, ledgers, saldos o modelos financieros paralelos.
- No exponer campos técnicos al usuario ordinario si el sistema puede derivarlos.

## Criterio de terminado

Un requisito solo puede marcarse `IMPLEMENTADO Y VALIDADO` si existe evidencia acumulada de código real, integración, pruebas positivas y negativas, permisos server-side, auditoría, manejo de errores, documentación, commit, SHA verificable en `main` y CI verde para ese mismo SHA. Las integraciones con credenciales o servicios externos se clasifican como `IMPLEMENTADO — ACTIVACIÓN EXTERNA PENDIENTE` hasta ejecutar una prueba real autorizada.

## Próxima prioridad operativa

1. Confirmar remoto oficial y publicar el lote documental sin sobrescribir cambios ajenos.
2. Ejecutar validadores y pruebas dirigidas de documentación/gobierno disponibles en el entorno.
3. Corregir cualquier estado documental fuera del catálogo permitido que afecte documentos canónicos raíz.
4. Mantener la matriz raíz como resumen canónico y la matriz amplia de `docs/nexora/` como antecedente trazable hasta que un validador unifique ambas.
