# Arquitectura objetivo NEXORA

## Principio rector

NEXORA es el producto visible. ERPNext/Frappe es el motor técnico interno.

El usuario debe reconocer una única plataforma en escritorio, móvil y PWA. Los servicios nativos de ERPNext/Frappe se reutilizan cuando aportan documentos, permisos, colas, impresión, archivos, auditoría o persistencia.

## Capas

### Presentación

- Shell único NEXORA.
- Navegación escritorio y móvil.
- PWA.
- Identidad y contexto de proyecto.

### Aplicación

- Fondos y operaciones.
- Tesorería.
- Gastos y pagos.
- Contratos.
- Planificación y avance.
- Materiales e inventario.
- Compras.
- Reportes.
- Usuarios y seguridad.
- Integraciones.

### Motor técnico

ERPNext/Frappe conserva:

- DocTypes.
- Roles y permisos.
- Archivos.
- Colas.
- Impresión.
- Persistencia.
- Auditoría técnica.

## Evolución

Los nombres técnicos heredados de ConstruControl pueden mantenerse temporalmente cuando sean dependencias internas. Su sustitución requiere validación de rutas, activos y compatibilidad.

## Reglas

- No modificar producción sin autorización.
- No eliminar datos históricos.
- Validar permisos en backend.
- Mantener migraciones trazables.
