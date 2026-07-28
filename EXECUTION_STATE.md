# NEXORA — Estado de ejecución

- Fecha: 2026-07-27
- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama base: `main`
- HEAD base verificado: `e4c896c5dd9aaf7d345bcfec3e7253afc82fddbf`
- Rama técnica: `fix/nexora-fund-selector`
- Producción, AWS, Coolify, DNS, secretos, volúmenes y datos productivos modificados: **NO**
- Migración de registros históricos: **NO**

## Último bloque fusionado — NXR-EXEC-005

Estado: **IMPLEMENTADO Y VALIDADO**.

- PR: `#22`.
- Commit de fusión en `main`: `e4c896c5dd9aaf7d345bcfec3e7253afc82fddbf`.
- Resultado: ingresos netos correctos, tarjeta separada de anulaciones oculta y auditoría financiera preservada.

## Bloque actual — NXR-FND-0013

Estado: **IMPLEMENTADO, VALIDACIÓN CI PENDIENTE**.

### Defecto confirmado

El campo **Fondo que pagará** del diálogo rápido de gastos utilizaba un `Select` nativo dinámico. En el entorno real no desplegaba las opciones y mostraba únicamente una franja negra.

Clasificación anterior: **EXISTENTE PERO DEFECTUOSO**.

### Corrección implementada

- reemplazo del `Select` por `Autocomplete` de Frappe;
- carga de fondos mediante `nexora.financial.service.list_source_balances`;
- detalle visible de disponible, saldo y reservado;
- estados explícitos de carga, lista vacía y error;
- selector y guardado bloqueados cuando no existen fuentes elegibles;
- rechazo de valores escritos manualmente o pertenecientes a una consulta anterior;
- conservación de vista previa, ejecución central, idempotencia y validaciones financieras de servidor.

### Pruebas incorporadas

- contractual: el campo `source` usa `Autocomplete` y no `Select`;
- contractual: las opciones se cargan mediante `set_data`;
- contractual: existen estados de carga, vacío y error;
- contractual negativa: un valor no incluido en la respuesta del servidor es rechazado;
- Frappe/MariaDB positiva: una fuente activa aparece con saldo, reservado y disponible;
- Frappe/MariaDB negativas: una fuente anulada y una fuente de otro proyecto no aparecen;
- Frappe/MariaDB negativa: un proyecto vacío devuelve `[]`;
- permiso negativo: `Guest` recibe `frappe.PermissionError`.

### Evidencia publicada en rama

- interfaz: `nexora_app/nexora/public/js/nexora_quick_flows.js`;
- pruebas contractuales: `nexora_app/nexora/tests/test_quick_flows_contract.py`;
- pruebas reales: `nexora_app/nexora/tests/test_fund_selector_integration.py`;
- CI: `.github/workflows/nexora-financial.yml`;
- especificación: `docs/nexora/NXR-FND-0013_SELECTOR_FONDOS_GASTO.md`.

### Pendiente

1. abrir PR hacia `main`;
2. ejecutar contratos, sintaxis JavaScript, Frappe/MariaDB, linters, seguridad y navegador real;
3. corregir cualquier fallo real;
4. actualizar esta evidencia con PR, runs y SHA final;
5. fusionar únicamente con todas las compuertas aplicables aprobadas.

## Siguiente acción

Certificar exclusivamente `NXR-FND-0013`; no iniciar otro bloque antes de cerrar pruebas, PR y SHA verificable.
