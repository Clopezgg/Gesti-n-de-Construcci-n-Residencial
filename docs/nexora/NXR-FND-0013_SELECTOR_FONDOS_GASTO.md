# NXR-FND-0013 — Selector operativo de fondos para gastos

## Estado

**IMPLEMENTADO, VALIDACIÓN CI PENDIENTE**.

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

## Pruebas positivas

- Una fuente activa de HNL 100,000.00 aparece para su proyecto con saldo, reservado y disponible.
- El control usa `Autocomplete` y recibe opciones mediante `set_data`.
- Una fuente seleccionada desde la lista habilita el guardado.

## Pruebas negativas

- Una fuente anulada no aparece.
- Una fuente perteneciente a otro proyecto no aparece.
- Un proyecto sin fondos devuelve una lista vacía y mantiene bloqueado el guardado.
- Un usuario `Guest` no puede consultar saldos.
- Un valor escrito manualmente o perteneciente a una lista anterior es rechazado antes de crear la operación.
- El control nativo defectuoso `Select` no vuelve a utilizarse para `source`.

## Criterio verificable de terminado

Se considerará **IMPLEMENTADO Y VALIDADO** únicamente cuando el código esté publicado, las pruebas contractuales y Frappe/MariaDB aprueben, los linters y controles de seguridad estén en verde, el PR se fusione y exista un SHA verificable en `main`.
