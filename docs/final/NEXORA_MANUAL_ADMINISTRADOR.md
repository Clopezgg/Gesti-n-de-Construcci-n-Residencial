# NEXORA — Manual del administrador

## Responsabilidad

El administrador mantiene usuarios, roles, proyectos, catálogos, permisos, integridad y operación. No debe modificar documentos financieros ejecutados por SQL, consola o edición directa.

## Usuarios y roles

1. Cree o active el usuario en Frappe.
2. Asigne únicamente los roles NEXORA necesarios para su función.
3. Limite acceso por proyecto cuando corresponda.
4. Pruebe el acceso con el usuario real: navegación visible y rechazo server-side.
5. Desactive cuentas que ya no deban operar; no reutilice identidades.

Mantenga segregadas las funciones de solicitud, aprobación, ejecución, auditoría y administración. Ocultar un botón no sustituye el permiso del servidor.

## Catálogos

Administre tipos de operación, categorías económicas, centros de costo, proyectos, fases, monedas, unidades, artículos y perfiles de proveedor. Antes de desactivar un catálogo revise documentos activos que lo referencien.

## Fondos y operaciones

Los saldos se derivan de `NXR Operation Effect` y del Libro Central. No cree saldos manuales ni hojas paralelas como fuente oficial. Para una diferencia, ejecute conciliación y utilice una corrección autorizada.

## Contratos, compras e inventario

- Verifique vigencia y cumplimiento de contratistas/proveedores.
- Controle presupuestos y compromisos antes de aprobar.
- No permita sobreentregas, inventario negativo ni sobrepagos sin flujo formal.
- Adjunte evidencia privada cuando la política lo exija.

## Cierres y auditoría

Ejecute cierres después de conciliar saldos, pendientes, compromisos e inventario. Los cierres son inmutables; una corrección posterior debe usar documento compensatorio y conservar trazabilidad.

## Validación después de actualizar

Toda actualización debe corresponder a un SHA aprobado de `main`. Confirme:

- migración repetida;
- instalación y reinicio;
- permisos;
- dashboard y flujos principales;
- iPhone/PWA;
- backup y restauración;
- workflows verdes del SHA desplegado.

## Incidentes

Ante fallo de integridad o seguridad, detenga nuevas operaciones del flujo afectado, preserve logs/evidencia, haga respaldo y documente el SHA y la hora. No borre registros para ocultar el problema.
