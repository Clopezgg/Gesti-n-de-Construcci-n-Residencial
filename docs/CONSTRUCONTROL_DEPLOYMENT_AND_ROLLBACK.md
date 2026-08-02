# NEXORA — Despliegue y reversión segura

## Fuente única de verdad

La rama `main` contiene código, definiciones runtime, migraciones, activos PWA, validaciones y documentación de NEXORA.

ERPNext/Frappe actúa como motor técnico interno. AWS y Coolify construyen y ejecutan la versión aprobada del repositorio.

## Antes de desplegar

- Confirmar SHA exacto.
- Validar pruebas disponibles.
- Confirmar estado saludable de servicios.
- No modificar volúmenes persistentes sin autorización.

## Despliegue

La aplicación visible es NEXORA. Las rutas y nombres técnicos heredados de ConstruControl pueden mantenerse temporalmente cuando sean necesarios para compatibilidad.

## Reversión

Las reversiones deben realizarse mediante commits versionados, conservando datos y volúmenes existentes.

No eliminar manualmente volúmenes, tablas, secretos o archivos productivos.

## Evidencia de cierre

- SHA desplegado.
- Resultado de validaciones.
- Estado saludable de servicios.
- Evidencia operativa.
