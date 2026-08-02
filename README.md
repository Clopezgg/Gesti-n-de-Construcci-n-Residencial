# NEXORA — Gestión Integral de Fondos, Proyectos y Operaciones

NEXORA es la plataforma empresarial para la gestión integral de fondos, proyectos y operaciones.

La base tecnológica utiliza **ERPNext / Frappe** como motor técnico interno cuando corresponde. ERPNext/Frappe no representa el producto comercial; funciona como infraestructura tecnológica sobre la cual se construyen los módulos y flujos NEXORA.

## Fuente única de verdad

- Repositorio: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama productiva protegida: `main`
- Despliegue productivo: `docker-compose.yml`
- Infraestructura: AWS EC2 + Ubuntu + Coolify
- Plataforma de contenedor: `linux/amd64`
- Base productiva: MariaDB 10.6
- Servicios técnicos: Redis, backend, workers, scheduler, WebSocket y frontend

## Arquitectura

NEXORA mantiene una arquitectura empresarial basada en ERPNext/Frappe e incorpora módulos especializados para:

- fondos y operaciones financieras;
- proyectos y centros de costo;
- contratos y proveedores;
- inventario;
- auditoría y permisos;
- reportes y seguimiento operativo.

## Módulos

Los módulos existentes deben interpretarse dentro de la evolución hacia NEXORA. Las aplicaciones técnicas heredadas de ERPNext/Frappe permanecen como componentes internos mientras sean necesarias para la operación.

## Seguridad y operación

Cada operación crítica debe validarse desde backend, conservar trazabilidad y respetar permisos definidos por usuario, proyecto y documento.

No se realizan modificaciones de producción, infraestructura, secretos o datos reales sin autorización, respaldo verificable y plan de reversión.

## Certificación

La plataforma se valida mediante pruebas técnicas, permisos, integridad financiera, recorridos operativos y controles de despliegue antes de considerar una funcionalidad terminada.
