# BLOQUE 2 — Consolidación de páginas, rutas y propietarios de interfaz

## Alcance

Se auditó la creación de páginas ConstruControl, los controladores JavaScript, los instaladores, los registros `Page` y los destinos declarados en los assets runtime.

## Hallazgo principal

Existían cuatro escritores independientes para los mismos registros `Page`:

1. `integration.py` creaba páginas desde `runtime/assets.json`.
2. `reporting_install.py` insertaba `construcontrol-reporting-center` con JavaScript embebido.
3. `weekly_install.py` insertaba `construcontrol-weekly-closing` con JavaScript embebido.
4. `product_pages.py` creaba cuatro páginas adicionales.

Los scripts almacenados en base de datos habían quedado desfasados respecto de los controladores del sistema de archivos. Esto permitía que una migración reinstalara implementaciones antiguas, causara páginas paralelas o produjera errores de nombre y duplicación.

## Implementación oficial

El propietario único de los registros `Page` es ahora:

`erpnext/construcontrol/page_registry.py`

El registro canónico:

- declara exactamente ocho páginas;
- valida nombres únicos y coincidencia entre `name` y `page_name`;
- valida roles no vacíos y sin duplicados;
- exige un controlador físico por página;
- comprueba que cada controlador registre su ruta exacta en `frappe.pages`;
- deja el campo de base de datos `script` vacío;
- actualiza roles y metadatos de forma idempotente.

Los controladores oficiales permanecen únicamente en:

`erpnext/construcontrol/page/<nombre_normalizado>/<nombre_normalizado>.js`

## Páginas canónicas

1. `construcontrol-dashboard`
2. `construcontrol-migration-console`
3. `construcontrol-reporting-center`
4. `construcontrol-weekly-closing`
5. `construcontrol-profile`
6. `construcontrol-project-center`
7. `construcontrol-users`
8. `construcontrol-integrations`

## Cambios aplicados

- `install.py` ejecuta una sola escritura canónica de páginas después de instalar campos operativos, reportes y cierre semanal.
- `integration.py` dejó de crear páginas.
- `reporting_install.py` conserva únicamente campos de reportes/notificaciones.
- `weekly_install.py` conserva únicamente campos de cierre semanal.
- `product_pages.py` queda como entrada de compatibilidad que delega al registro canónico, pero no es invocada por la instalación.
- `runtime/assets.json` contiene metadatos y roles de las ocho páginas, sin JavaScript embebido.
- El validador de finalización exige la nueva arquitectura.

## Pruebas

- 109/109 pruebas standalone aprobadas.
- 7 validadores de repositorio, gobierno, integración, finalización, arquitectura, datos y producto aprobados.
- Compilación Python aprobada.
- Sintaxis JavaScript de todas las páginas aprobada.
- Ruff aprobado en los archivos modificados.
- Prueba específica del registro canónico: 4/4 aprobada.

## Evidencia Git

- Implementación: `e96213b6b931f528066abb6cd809b59da64c0527`
- Regresión runtime adicional: `04bf6111766e4103ac9148dab181f71a99b537d9`
- Pull Request: #9

## Estado

La consolidación de páginas está implementada y publicada. La aprobación remota integral permanece pendiente del ciclo de GitHub Actions del HEAD vigente; no se declara cierre remoto hasta que termine.
