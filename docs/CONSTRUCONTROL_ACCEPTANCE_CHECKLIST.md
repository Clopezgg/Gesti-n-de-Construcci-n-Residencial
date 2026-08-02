# NEXORA — Lista de aceptación final

Esta lista debe completarse con la versión exacta desplegada.

## Identidad y arquitectura

- [ ] NEXORA es la interfaz visible principal del producto.
- [ ] ERPNext/Frappe funciona como motor técnico interno.
- [ ] Los componentes técnicos heredados conservan compatibilidad mientras sean necesarios.
- [ ] GitHub `main` contiene los cambios desplegados.
- [ ] No existen parches manuales permanentes en AWS o Coolify.

## Datos y operación

- [ ] Los contratos runtime se validan antes de cambios de datos.
- [ ] Las migraciones son trazables e idempotentes.
- [ ] Los datos existentes se conservan.
- [ ] Existe respaldo verificable antes de operaciones críticas.

## Experiencia

- [ ] Escritorio, móvil y PWA presentan identidad NEXORA.
- [ ] ERPNext no compite como navegación principal del usuario.
- [ ] Los módulos empresariales utilizan navegación coherente.

## Seguridad y entrega

- [ ] Validadores y pruebas finalizan correctamente.
- [ ] Python, JavaScript y configuraciones son válidos.
- [ ] La imagen y despliegue reproducible mantienen las reglas de infraestructura.

Nota: algunos nombres técnicos heredados pueden conservarse temporalmente cuando cambiarlo afecte rutas, activos o compatibilidad. Su migración requiere validación independiente.
