# NEXORA — Estado de ejecución

- Fecha: 2026-07-28
- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama base: `main`
- HEAD base verificado: `e4c896c5dd9aaf7d345bcfec3e7253afc82fddbf`
- Rama técnica: `fix/nexora-fund-selector`
- Pull Request: `#23`
- Producción, AWS, Coolify, DNS, secretos, volúmenes y datos productivos modificados: **NO**
- Migración de registros históricos: **NO**

## Último bloque fusionado — NXR-EXEC-005

Estado: **IMPLEMENTADO Y VALIDADO**.

- PR: `#22`.
- Commit de fusión en `main`: `e4c896c5dd9aaf7d345bcfec3e7253afc82fddbf`.
- Resultado: ingresos netos correctos, tarjeta separada de anulaciones oculta y auditoría financiera preservada.

## Bloque actual — NXR-FND-0013

Estado: **CERTIFICADO EN RAMA, FUSIÓN PENDIENTE**.

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
- conservación de vista previa, ejecución central, idempotencia y validaciones financieras de servidor;
- validador real de navegador para escritorio Chromium, iPhone WebKit y PWA.

### Pruebas positivas y negativas aprobadas

- contractual: el campo `source` usa `Autocomplete` y no `Select`;
- contractual: las opciones se cargan mediante `set_data`;
- contractual: existen estados de carga, vacío y error;
- contractual negativa: un valor no incluido en la respuesta del servidor es rechazado;
- Frappe/MariaDB positiva: una fuente activa aparece con saldo, reservado y disponible;
- Frappe/MariaDB negativas: una fuente anulada y una fuente de otro proyecto no aparecen;
- Frappe/MariaDB negativa: un proyecto vacío devuelve `[]`;
- permiso negativo: `Guest` recibe `frappe.PermissionError`;
- navegador real: el selector muestra opciones legibles con Disponible, Saldo y Reservado;
- navegador real: no existe el `select` nativo defectuoso;
- navegador real: una fuente válida se selecciona y habilita **Guardar gasto** en escritorio e iPhone.

### Evidencia certificada

- SHA funcional probado: `02e6b1f4d1ab79594164de4d60274f5a725d56c3`;
- PR: `#23`;
- NEXORA app, instalación, rollback, escritorio, iPhone y PWA: run `30319502624`, aprobado;
- invariantes financieras Frappe/MariaDB y concurrencia: run `30319502613`, aprobado;
- linters y Semgrep: run `30319502636`, aprobado;
- Patch: run `30319502631`, aprobado;
- gobierno NEXORA: run `30319502622`, aprobado;
- documentación requerida: run `30319502617`, aprobado;
- commits semánticos: run `30319502627`, aprobado;
- controles estáticos de servidor y parches: runs `30319502661` y `30319502660`, aprobados;
- validación heredada de coexistencia: run `30319502619`, aprobado.

### Archivos principales

- interfaz: `nexora_app/nexora/public/js/nexora_quick_flows.js`;
- pruebas contractuales: `nexora_app/nexora/tests/test_quick_flows_contract.py`;
- pruebas reales: `nexora_app/nexora/tests/test_fund_selector_integration.py`;
- navegador real: `scripts/nexora_browser_smoke.mjs`;
- CI: `.github/workflows/nexora-financial.yml`;
- especificación: `docs/nexora/NXR-FND-0013_SELECTOR_FONDOS_GASTO.md`.

### Pendiente

1. validar este cierre documental sobre el HEAD final del PR;
2. marcar el PR `#23` listo para revisión;
3. fusionar únicamente si todas las compuertas aplicables continúan aprobadas;
4. registrar el SHA de fusión en la entrega ejecutiva.

## Siguiente acción

Cerrar exclusivamente `NXR-FND-0013` mediante la fusión del PR `#23`; no iniciar otro bloque antes de publicar y verificar el SHA final en `main`.
