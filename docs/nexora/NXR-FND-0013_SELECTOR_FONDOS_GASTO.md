# NXR-FND-0013 — Selector operativo de fondos para gastos

## Estado

**CERTIFICADO EN RAMA, FUSIÓN PENDIENTE**.

- PR: `#23`.
- SHA funcional probado: `02e6b1f4d1ab79594164de4d60274f5a725d56c3`.
- NEXORA app, instalación, rollback, escritorio, iPhone y PWA: run `30319502624`, aprobado.
- Frappe/MariaDB, invariantes financieras y concurrencia: run `30319502613`, aprobado.
- Linters y Semgrep: run `30319502636`, aprobado.
- Patch: run `30319502631`, aprobado.

## Decisión anterior

El diálogo rápido de gasto utilizaba un control nativo `Select` actualizado dinámicamente. En el entorno real mostrado por el usuario, el control no desplegaba las opciones y presentaba únicamente una franja negra.

Clasificación: **EXISTENTE PERO DEFECTUOSO**.

## Corrección vigente

El campo **Fondo que pagará** utiliza un control Frappe `Autocomplete`, alimentado por el endpoint real `nexora.financial.service.list_source_balances`.

El selector debe:

- cargar fondos después de seleccionar el proyecto;
- mostrar el código del fondo;
- mostrar saldo disponible, saldo total y monto reservado;
- aceptar únicamente valores devueltos por el servidor;
- mostrar estados legibles de carga, lista vacía y error;
- permanecer deshabilitado cuando no existan fondos disponibles;
- impedir guardar el gasto sin una fuente válida;
- conservar la validación financiera definitiva en el servidor.

## Flujo operativo

1. El usuario selecciona el proyecto.
2. La interfaz bloquea temporalmente el selector y el botón de guardado.
3. Se consulta `list_source_balances(project)` mediante `POST`.
4. Solo se presentan fuentes cuyo `available_hnl` sea mayor que cero.
5. El usuario selecciona una fuente de la lista autocompletada.
6. El botón **Guardar gasto** se habilita únicamente cuando el valor pertenece al conjunto recibido.
7. La vista previa y la ejecución central vuelven a validar saldo, asignación y permisos en servidor.

## Permisos

El endpoint conserva `read_balances`; un usuario invitado debe recibir `frappe.PermissionError`. La consulta se filtra por el proyecto solicitado y no presenta fuentes anuladas ni fuentes de otros proyectos.

## Pruebas positivas aprobadas

- Una fuente activa de HNL 100,000.00 aparece para su proyecto con saldo, reservado y disponible.
- El control usa `Autocomplete` y recibe opciones mediante `set_data`.
- Una fuente seleccionada desde la lista habilita el guardado.
- El navegador real muestra Disponible, Saldo y Reservado en escritorio Chromium e iPhone WebKit.
- La PWA conserva el mismo flujo operativo.

## Pruebas negativas aprobadas

- Una fuente anulada no aparece.
- Una fuente perteneciente a otro proyecto no aparece.
- Un proyecto sin fondos devuelve una lista vacía y mantiene bloqueado el guardado.
- Un usuario `Guest` no puede consultar saldos.
- Un valor escrito manualmente o perteneciente a una lista anterior es rechazado antes de crear la operación.
- El control nativo defectuoso `Select` no vuelve a utilizarse para `source`.
- La prueba visual confirma que el texto de cada opción es distinguible del fondo y que no reaparece la franja negra.

## Criterio verificable de terminado

El código, las pruebas contractuales, Frappe/MariaDB, navegador real, linters, Semgrep, Patch, gobierno y documentación están aprobados en la rama. Se declarará **IMPLEMENTADO Y VALIDADO** después de fusionar el PR `#23` y verificar el SHA publicado en `main`.
