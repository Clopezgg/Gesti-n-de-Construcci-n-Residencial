# Deuda de validación controlada

Ninguna fila equivale a aprobación. El workflow de certificación elimina la deuda únicamente cuando la puerta correspondiente finaliza correctamente sobre el SHA congelado y publica evidencia.

| Identificador | Módulo | SHA | Prueba o workflow | Severidad | Evidencia previa | Puerta | Estado inicial |
|---|---|---|---|---|---|---|---|
| VAL-A-001 | FI01/FI02/PR01/CO01 | HEAD congelado por `freeze` | MariaDB 4/4, permisos, cálculos, migraciones y runtime | Alta | Pruebas dirigidas y commits funcionales | A | Pendiente |
| VAL-B-001 | MM01/MM02/MIGO/QC01/CL01/BI01/AU01 | HEAD congelado por `freeze` | Comportamiento, MariaDB, relaciones, cierres, dashboard y auditoría | Alta | Pruebas dirigidas de Bloques 8–10 | B | Pendiente |
| VAL-C-001 | UI/PWA/Infra/MIG/Backup/Restore | HEAD congelado por `freeze` | Stack completo, reinicio, persistencia, backup y restore aislado | Alta | Contratos rápidos de Bloques 11–12 | C | Pendiente |
| VAL-FINAL-001 | Sistema completo | HEAD congelado por `freeze` | Instalación limpia, actualización, tres migraciones, redeploy y restore | Crítica | Requiere A, B y C verdes | FINAL | Pendiente |
| VAL-AUDIT-001 | Cobertura 1:1 | HEAD congelado por `freeze` | Auditoría independiente, behavior tests y snapshot reproducible | Crítica | Requiere FINAL verde | AUDIT_1_TO_1 | Pendiente |

## Regla de cierre

Una deuda se considera cerrada únicamente si:

- el job obligatorio concluye `success`;
- el SHA coincide con el congelado;
- los artifacts existen;
- no hay prueba cancelada;
- no hay resultado manual;
- no hay requisito externo sin demostrar.
