# NEXORA — Corrección guiada de operaciones contabilizadas

## Requisitos trazables

- `NXR-COR-20260728-01`: **CONFIRMADO**. Una operación de ingreso contabilizada se corrige buscando su número documental único de 12 dígitos; no se edita libremente desde el formulario canónico.
- `NXR-COR-20260728-02`: **CONFIRMADO**. La búsqueda carga fecha documental, nombre de remesa o fuente, canal, moneda, valor original, tasa, importe HNL, remitente, banco o remesadora, cuenta, referencia y comprobante.
- `NXR-COR-20260728-03`: **CONFIRMADO**. Cambiar fecha o metadatos no exige evidencia; el comprobante es opcional y solo sustituye al anterior cuando el usuario adjunta uno.
- `NXR-COR-20260728-04`: **CONFIRMADO**. Cambiar valor, moneda o tasa solo se permite si la fuente conserva íntegro su único efecto recibido y no tiene asignaciones, gastos, reservas, transferencias ni ajustes.
- `NXR-COR-20260728-05`: **CONFIRMADO**. Toda corrección genera un documento `304`, conserva el original, registra antes y después, actor, motivo, correlación, idempotencia y número documental nuevo.
- `NXR-COR-20260728-06`: **CONFIRMADO**. Solo Gerente financiero, Administrador NEXORA o System Manager puede buscar, previsualizar y ejecutar la corrección.
- `NXR-UX-20260728-03`: **CONFIRMADO**. La tabla **Últimas operaciones** debe mantener once encabezados y once celdas por fila aunque el dashboard base se vuelva a renderizar.

## Flujo operativo

1. El usuario autorizado pulsa **Corregir documento** o selecciona el código `304`.
2. Escribe el número documental de 12 dígitos.
3. NEXORA localiza la operación base y su fuente recibida.
4. El servidor devuelve los valores efectivos y señala si el importe puede modificarse.
5. El usuario cambia únicamente los campos necesarios y explica el motivo con al menos diez caracteres.
6. **Vista previa** valida permisos, proyecto, fecha futura, períodos cerrados, catálogo, uso posterior del fondo y vigencia de la lectura.
7. **Aplicar corrección** bloquea operación, fuente y efecto; genera el documento `304`; aplica los valores efectivos mediante una bandera interna restringida; registra auditoría e idempotencia; y confirma el número documental correctivo.

## Reglas financieras

- La edición directa de `NXR Operation`, `NXR Fund Source` y `NXR Operation Effect` continúa bloqueada.
- Una corrección de fecha o metadatos no crea ni elimina saldo.
- Una corrección de importe actualiza operación, fuente y efecto recibido dentro de la misma transacción y únicamente cuando el fondo no ha sido utilizado.
- Si el fondo ya fue utilizado, NEXORA mantiene habilitadas las correcciones no financieras y explica que los cambios de importe requieren documentos compensatorios previos.
- Una fecha corregida no puede ser futura.
- Si la fecha cambia, tanto el período anterior como el nuevo deben permanecer abiertos.
- Si cambia el importe, el período del ingreso debe permanecer abierto.
- No existe borrado físico.

## Evidencia

La evidencia es opcional para este flujo. Adjuntarla reemplaza el comprobante efectivo de la fuente y la operación base, pero no es requisito para corregir fecha, nombre, remitente, canal, banco, cuenta o referencia.

## Permisos

- Lectura, vista previa y ejecución: acción de servidor `reclassify`.
- Roles autorizados: `System Manager`, `NEXORA Administrator`, `NEXORA Finance Manager`.
- Operador financiero, auditor y visor no pueden ejecutar la corrección.
- El alcance de proyecto se valida nuevamente en servidor.

## Pruebas positivas requeridas

1. buscar un ingreso por número de 12 dígitos;
2. corregir fecha, nombre de remesa y remitente sin evidencia;
3. generar documento `304` con número único;
4. conservar antes y después en `NXR Audit Event`;
5. repetir la misma solicitud con idéntica clave de idempotencia sin duplicar documentos;
6. corregir el importe de una fuente íntegra y sincronizar fuente, operación y efecto;
7. mantener once columnas coherentes en **Últimas operaciones**.

## Pruebas negativas requeridas

1. rechazar número inexistente o que no contenga 12 dígitos;
2. rechazar operaciones que no sean ingresos base ejecutados;
3. rechazar usuarios sin rol de gerente o administrador;
4. rechazar fecha futura o período cerrado;
5. rechazar solicitudes sin cambios o sin motivo suficiente;
6. rechazar cambios de importe cuando el fondo tenga usos posteriores;
7. rechazar vista previa vencida o clave de idempotencia reutilizada con datos diferentes;
8. mantener bloqueada la edición directa y la eliminación de operaciones ejecutadas.

## Estado de implementación

Código, interfaz y pruebas están publicados en la rama `fix/nexora-guided-document-correction` sobre la base `4f24ad57cdcc1b322b268c1502ba0bfbb01511b3`. El estado permanecerá **CONFIRMADO** hasta que CI ejecute instalación, migración, pruebas positivas y negativas, navegador real, linters y Patch sobre un SHA publicado.
