# NEXORA — Estado de ejecución

- Fecha: 2026-07-28
- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama base: `main`
- HEAD base verificado para la corrección: `558c5fef779acdc55659cc44ea5c99dbdfd6124f`
- Rama técnica activa: `fix/nexora-financial-account-entry-ui`
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

Estado corregido por evidencia de uso real: **EXISTENTE PERO DEFECTUOSO**.

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

## Bloque correctivo actual — NXR-OPR-20260728-04 / NXR-UX-20260728-02

Estado: **CONFIRMADO**. Implementación preparada en la rama técnica; publicación y certificación pendientes.

### Alcance funcional

- separar explícitamente **Usar cuenta existente**, **Crear cuenta nueva** y **Datos manuales, no guardar**;
- ignorar de forma segura texto residual de cuenta cuando el modo sea cuenta nueva;
- rechazar cuentas inexistentes con mensaje accionable cuando el modo sea cuenta existente;
- limpiar la selección al cambiar de proyecto o modo;
- validar la cuenta nueva durante la vista previa y crearla en la misma transacción de contabilización;
- incorporar `Bank` como catálogo para banco o remesadora;
- conservar compatibilidad con el flujo anterior basado en `save_financial_account`;
- incluir modo y nombre de cuenta nueva en la huella de vista previa.

### Alcance de interfaz

- cabecera documental con pestañas **General** e **Info. documento**;
- tabla compacta de líneas del movimiento;
- detalle inferior por pestañas **Cuenta**, **Importe**, **Clasificación**, **Fondos** y **Evidencia**;
- mensajes de validación junto a los campos;
- explicación visible de por qué **Contabilizar** permanece deshabilitado;
- adaptación para escritorio, iPhone y PWA;
- identidad NEXORA sin copiar marcas, activos ni interfaz propietaria.

### Permisos y seguridad

- los permisos de servidor existentes permanecen obligatorios;
- `NXR Financial Account` continúa sin creación directa desde el DocType;
- la cuenta se crea mediante servicio financiero con auditoría y huella única;
- una cuenta de otro proyecto o con uso no permitido sigue siendo rechazada;
- no se elimina ninguna operación contabilizada;
- no se modifica producción ni infraestructura durante este bloque.

### Pruebas exigidas

Positivas:

1. crear la primera cuenta con modo **New** aunque exista texto residual en `financial_account`;
2. reutilizar una cuenta existente;
3. registrar datos manuales sin crear cuenta;
4. mostrar banco o remesadora mediante enlace al catálogo `Bank`;
5. renderizar cabecera, línea y detalle en escritorio y móvil.

Negativas:

1. rechazar una cuenta inexistente en modo **Existing** con mensaje accionable;
2. impedir vista previa sin cuenta existente seleccionada;
3. impedir vista previa de cuenta nueva sin nombre;
4. impedir remesa, depósito o transferencia sin institución, cuenta o referencia;
5. impedir contabilización sin vista previa vigente.

## Siguiente acción

Publicar el commit funcional de la rama, abrir un único Pull Request contra `main`, ejecutar todas las compuertas, corregir fallos reales, actualizar esta evidencia con SHA y fusionar únicamente después de la certificación.
