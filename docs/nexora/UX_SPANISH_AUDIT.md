# NEXORA — Auditoría de español visible

## Regla

La identidad visible de NEXORA debe permanecer en español. Identificadores técnicos, nombres internos de APIs, clases Python, `operation_type` internos y traducciones upstream de ERPNext no se consideran superficie visible de NEXORA.

## Superficies revisadas

- Dashboard y shell global.
- Workspace NEXORA.
- Fondos y operaciones.
- Contratos y proveedores.
- Compras y recepciones.
- Inventario.
- Evidencias y avance.
- Reportes y cierres.
- Asistente/canales.
- PWA y mensajes de error.

## Contrato observado

- Las nuevas acciones de compra usan `Registrar pago`, `Importe HNL`, `Clasificación económica`, `Evidencia`, `Descripción` y mensajes en español.
- El cierre mensual usa `Cierre mensual`, `Mes`, `Proyecto`, `Calcular y guardar`, `Actualizar historial`, `Disponible HNL`, `Huella` y `Corrige a`.
- Los textos heredados de ConstruControl no forman parte de la navegación ni identidad de NEXORA.
- Terminología financiera visible evita el uso de "ingreso" como categoría funcional de usuario, conservando únicamente identificadores internos donde son necesarios para compatibilidad/auditoría.

## Evidencia

La auditoría de código no encontró nuevas cadenas visibles de NEXORA en inglés para las superficies incorporadas en esta fase. La traducción upstream de ERPNext queda fuera de la identidad de NEXORA.

## Pendiente no bloqueante

La aprobación final del tono visual y del copy debe hacerse sobre una instancia desplegada real en la auditoría UX humana; CI no sustituye esa revisión.
