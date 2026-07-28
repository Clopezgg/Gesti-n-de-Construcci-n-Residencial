# NEXORA — Estado de ejecución

- Fecha: 2026-07-28
- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama base: `main`
- HEAD base verificado para la corrección: `558c5fef779acdc55659cc44ea5c99dbdfd6124f`
- Rama técnica activa: `fix/nexora-financial-account-entry-ui`
- Pull Request activo: `#27`
- Producción, AWS, Coolify, DNS, secretos, volúmenes y datos productivos modificados: **NO**
- Migración de registros históricos: **NO**

## Último bloque fusionado — NXR-EXEC-007 / NXR-USR-0007

Estado: **IMPLEMENTADO Y VALIDADO**.

- PR fusionado: `#25`.
- SHA funcional probado: `8ac970290df4d8cc675ab59d44ce22bd3ec85c27`.
- HEAD final certificado del PR: `deda757fa11163e5126aa0001aa20e6ade2729bf`.
- Commit de fusión publicado en `main`: `a3d47d6802944fe9dee6250e6a4d5bd4ba9126dd`.
- HEAD documental previo de `main`: `6812ee55f2aa1e723d9c59ea84675bf83b673990`.

## Bloque fusionado con defecto confirmado — Consola operativa, fechas, cuentas y Libro Central

Requisitos originales:

- `NXR-OPR-20260728-01` — fecha documental histórica;
- `NXR-OPR-20260728-02` — cuentas frecuentes reutilizables;
- `NXR-OPR-20260728-03` — consola numérica `101/102/303/304/501`;
- `NXR-LGR-20260728-01` — Libro Central operativo ampliado;
- `NXR-UX-20260728-01` — dashboard inferior compacto;
- `NXR-LGR-20260728-02` — semántica correctiva sin borrado físico.

Estado corregido por evidencia de uso real: **EXISTENTE PERO DEFECTUOSO** para el alta inicial de cuentas y la estructura visual de la consola.

### Defecto confirmado

- el control `Autocomplete` aceptaba texto libre en `financial_account`;
- cualquier texto no vacío se trataba como identificador de una cuenta existente;
- marcar **Guardar como cuenta frecuente** no anulaba ese valor;
- la búsqueda del documento inexistente fallaba antes de crear la cuenta;
- el selector no se limpiaba de forma inequívoca al cambiar de proyecto o de modo;
- banco o remesadora era texto libre, no catálogo;
- la pantalla no seguía la estructura cabecera–líneas–detalle solicitada;
- la vista previa fallida no señalaba de forma suficiente los campos bloqueantes.

### Evidencia histórica del bloque original

- PR fusionado: `#26`.
- SHA funcional probado: `b23d9b902191d5693e0841b39ba550ce7cb82d49`.
- HEAD final certificado del PR: `c0b9f9a06f8f9e3d4fc9e9b943abe5615b9c0755`.
- Commit de fusión publicado en `main`: `2e87a0b0ef967efccc3ee0969c095af873a32136`.
- La evidencia automatizada anterior no sustituyó la validación de uso real que reveló el defecto.

## Bloque correctivo — NXR-OPR-20260728-04 / NXR-UX-20260728-02

Estado: **IMPLEMENTADO Y VALIDADO** en PR `#27`; fusión a `main` pendiente de la ronda final de certificación del HEAD documental.

### Evidencia publicada

- Rama: `fix/nexora-financial-account-entry-ui`.
- PR: `#27`.
- SHA funcional probado: `d4b95dd2b9d86c67215a196c8f791a02f5d202ef`.
- Linters y Semgrep: run `30378266857`, aprobado.
- Aplicación NEXORA, contrato, instalación, migración, desinstalación/rollback, reinstalación, escritorio, iPhone y PWA: run `30378266892`, aprobado.
- Invariantes financieras Frappe/MariaDB: run `30378266897`, aprobado.
- Patch: run `30378266728`, aprobado.
- Gobierno: run `30378267473`, aprobado.
- Documentación: run `30378266880`, aprobado.
- Evidencia estática: run `30378266869`, aprobado.
- Control estático de servidor: run `30378267015`, aprobado.
- Control de patch no Python: run `30378266729`, aprobado.
- Validación segura: run `30378266726`, aprobado.
- Commits semánticos: run `30378266725`, aprobado.
- Postgres: run `30378266769`, omitido por diseño; MariaDB es la instalación canónica validada.

### Alcance funcional terminado

- modos explícitos **Usar cuenta existente**, **Crear cuenta nueva** y **Datos manuales, no guardar**;
- texto residual de `financial_account` ignorado de forma segura cuando el modo es cuenta nueva;
- cuentas inexistentes rechazadas con mensaje accionable en modo existente;
- selección limpiada al cambiar de proyecto o modo;
- cuenta nueva validada en vista previa y creada en la misma transacción de contabilización;
- `Bank` incorporado como catálogo para banco o remesadora;
- compatibilidad conservada con el flujo anterior basado en `save_financial_account`;
- modo y nombre de cuenta nueva incluidos en la huella de vista previa.

### Alcance de interfaz terminado

- cabecera documental con pestañas **General** e **Info. documento**;
- tabla compacta de líneas del movimiento;
- detalle inferior por pestañas **Cuenta**, **Importe**, **Clasificación**, **Fondos** y **Evidencia**;
- mensajes de validación asociados a los campos;
- explicación visible de por qué **Contabilizar** permanece deshabilitado;
- recorrido real validado en escritorio, iPhone y PWA;
- identidad NEXORA sin copiar marcas, activos ni interfaz propietaria.

### Permisos y seguridad

- los permisos de servidor existentes permanecen obligatorios;
- `NXR Financial Account` continúa sin creación directa desde el DocType;
- la cuenta se crea mediante servicio financiero con auditoría y huella única;
- una cuenta de otro proyecto o con uso no permitido sigue siendo rechazada;
- no se elimina ninguna operación contabilizada;
- no se modificó producción ni infraestructura.

### Pruebas positivas aprobadas

1. crear la primera cuenta con modo `New` aunque exista texto residual en `financial_account`;
2. reutilizar una cuenta existente;
3. conservar modo manual sin crear cuenta;
4. mostrar banco o remesadora mediante enlace al catálogo `Bank`;
5. renderizar cabecera, línea y detalle;
6. instalar, migrar, retirar, reinstalar y sembrar NEXORA de forma idempotente;
7. validar escritorio, iPhone y PWA reales.

### Pruebas negativas aprobadas

1. rechazar una cuenta inexistente en modo `Existing` con mensaje accionable;
2. impedir vista previa sin cuenta existente seleccionada;
3. impedir vista previa de cuenta nueva sin nombre;
4. impedir remesa, depósito o transferencia sin institución, cuenta o referencia;
5. impedir contabilización sin vista previa vigente;
6. conservar controles de proyecto, período cerrado, permisos y auditoría.

## Siguiente acción

Ejecutar la ronda final de CI sobre el commit documental de certificación, marcar el PR `#27` listo, fusionarlo con HEAD esperado, registrar el SHA de fusión y verificar el nuevo HEAD de `main`. El despliegue en Coolify permanece fuera de este bloque y requiere autorización expresa, respaldo, rollback y validación posterior.
