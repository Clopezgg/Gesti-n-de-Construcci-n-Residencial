# Auditoría integral de origen y destino

Fecha de auditoría: 2026-07-17.

## Integridad de los ZIP

| Archivo | SHA-256 | Entradas | Tamaño descomprimido |
|---|---|---:|---:|
| SISTEMA DE ORIGEN.zip | `4B4872708BE1224FAC79D509B8CD48208E0556BD3AD07E9974C6578780DFFCBE` | 284 | 1,274,332 bytes |
| SISTEMA DESTINO.zip | `9B9E2B281C203F83A0AD567BD8C73B0217FB8BB2F8B792B21468D2F8D540A2C8` | 5,789 | 71,233,973 bytes |

No se encontraron rutas absolutas, `..` ni rutas de escape en los ZIP. El destino contiene 4,613 archivos y 1,176 directorios.

## Sistema de origen

- Aplicación SPA React 19.1.1, TypeScript 5.9.2 y Vite 7.1.3.
- UI basada en UI5/Fiori y `@supabase/supabase-js` 2.52.1.
- Persistencia primaria en un snapshot `AppData` dentro de `localStorage`; sincronización opcional del JSON completo en `public.construction_projects.data`.
- SQL adicional para perfiles, versiones, auditoría, sesiones, socios, catálogo, cuentas por pagar, plantillas, reglas/ejecuciones de automatización y Storage.
- Autenticación Supabase, perfiles por proyecto, roles, políticas RLS y bucket privado `construction-evidence`.
- Módulos funcionales: proyectos/fases, ingresos, egresos, contratos, materiales e inventario, avance, cierres, reportes, notificaciones, auditoría y usuarios; además compras, equipo, órdenes de cambio, aprobaciones y plataforma empresarial.

Hallazgos de calidad:

- `prepare:types` modifica cinco archivos TypeScript al instalar/probar; el ZIP no es inmutable durante su propia preparación.
- Las suites incluidas son principalmente verificaciones por contenido/subcadenas, no pruebas end-to-end. Se ejecutaron 356 aserciones y pasaron.
- La compilación TypeScript real falla: `src/lib/fioriTheme.ts` importa `@ui5/webcomponents-base/dist/config/Theme.js`, dependencia directa no declarada.
- No se detectaron secretos reales en el árbol; existen variables y valores de ejemplo.
- No existe dump de datos, exportación de `localStorage` ni contenido de Storage. `EMPTY_DATA` aporta seis fases de configuración y colecciones operativas vacías.

## Sistema destino

- ERPNext 15.117.0 como aplicación Frappe; Python >=3.10 y Frappe >=15.40.4,<16.
- Veintiún módulos ERPNext y DocTypes estándar para Project, Task, Contract, Supplier, Item, Warehouse, Stock Entry, Asset, Material Request, Purchase Order/Receipt/Invoice, pagos, contabilidad, calidad e incidencias.
- Autenticación, sesiones, roles, permisos por DocType/documento, auditoría, workflows, informes y trabajos programados nativos de Frappe.
- No incluía configuración de Render ni una capa ConstruControl.
- Validación estática previa: 1,093 JSON válidos y 2,433 archivos Python sin errores de sintaxis AST.

## Conflictos y decisiones

| Conflicto | Decisión aplicada |
|---|---|
| SPA/localStorage frente a Frappe/ORM | ERPNext permanece como plataforma; no se incrusta ni copia la SPA. |
| Snapshot JSON frente a modelo relacional | Preservación íntegra versionada más mapeo controlado a DocTypes. |
| Auth/RLS de Supabase frente a permisos Frappe | Frappe es la autoridad de acceso; Supabase queda como fuente/Storage server-only. |
| Roles incompatibles | Tabla explícita a cuatro roles ConstruControl; usuarios desactivados por defecto. |
| Documentos financieros/stock históricos ambiguos | No se publican asientos ni movimientos; se preservan y se preparan solamente borradores cuando existe autorización. |
| Archivos distribuidos en Render | Hook de archivos a bucket Supabase privado, con descarga autorizada desde Frappe. |
| PostgreSQL disponible en Render | Se conserva MariaDB 10.6 porque Frappe 15 declara soporte PostgreSQL limitado. |

## Datos que realmente se pudieron migrar

No había registros reales dentro de los ZIP. Se trasladó al repositorio la definición de seis fases como fixture de referencia, sin presentarla como historial operativo. El importador queda listo para procesar todos los grupos de entidades hallados y bloqueará la importación real cuando falten archivos referenciados.

## Elementos obsoletos o no trasladados

- El frontend React/UI5, service worker y almacenamiento local no se incorporaron: ERPNext ofrece la interfaz, PWA/sesiones y formularios definitivos.
- No se trasladan contraseñas, PIN, tokens ni claves privadas.
- Las implementaciones duplicadas de reportes, notificaciones, permisos y auditoría se sustituyen por capacidades Frappe/ERPNext y por la capa de conciliación.
- No se copian `node_modules`, temporales, builds, respaldos ni `.env`.
