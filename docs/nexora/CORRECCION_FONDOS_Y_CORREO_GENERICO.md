# NEXORA — Corrección de Fondos y remesas y correo genérico

## Requisitos trazables

- `NXR-EXEC-007`: **IMPLEMENTADO, VALIDACIÓN CI PENDIENTE**. La tarjeta **Fondos y remesas** presenta cada fuente en una fila legible, sin superposición entre nombre, canal, fecha y saldo.
- `NXR-USR-0007`: **IMPLEMENTADO, VALIDACIÓN CI PENDIENTE**. El inicio de sesión no solicita contraseña para cuentas de correo NEXORA explícitamente genéricas, sin desactivar la validación de cuentas reales.

## Defecto confirmado — tarjeta Fondos y remesas

La página del dashboard reutilizaba simultáneamente las clases `nxr-balance-row` y `nxr-funds-list`. La primera pertenece a una cuadrícula histórica de cuatro columnas, mientras que la segunda contiene una lista de fuentes. La regla histórica convertía las fuentes en columnas estrechas y provocaba que nombres y saldos se superpusieran.

### Corrección

- se carga `nexora_dashboard_fixes.css` después de los estilos generales;
- la lista de fondos se fuerza a una sola columna;
- cada fuente usa dos columnas internas: información flexible y saldo de ancho estable;
- los nombres pueden partirse sin invadir el saldo;
- el importe conserva `white-space: nowrap`;
- en pantallas pequeñas, el saldo pasa debajo del nombre.

## Defecto confirmado — contraseña de correo al ingresar

Frappe muestra el diálogo **Falta contraseña en la cuenta de correo** cuando el valor de sesión `email_user_password` incluye al usuario actual y existe un registro `User Email` pendiente de contraseña.

La dirección `admin@nexora.com` es un identificador genérico de NEXORA y no una cuenta SMTP operativa que deba bloquear el acceso diario.

### Corrección

- se registra el hook `boot_session`;
- el hook revisa exclusivamente los registros `User Email` pendientes del usuario actual;
- el aviso se omite únicamente cuando todos los correos pendientes pertenecen a la lista cerrada de direcciones genéricas NEXORA:
  - `admin@nexora.com`;
  - `noreply@nexora.local`;
- si existe un correo real o una combinación de correo genérico y real, Frappe conserva su validación normal;
- no se modifica, elimina ni actualiza ningún registro `User`, `User Email` o `Email Account`;
- no se altera la contraseña de inicio de sesión ni la autenticación del usuario.

## Pruebas positivas

1. Dos o más fondos se muestran verticalmente y el saldo no invade el nombre.
2. Un nombre largo puede partirse y el saldo permanece completo.
3. En móvil, el saldo pasa a una línea independiente.
4. Un usuario marcado por Frappe únicamente por `admin@nexora.com` deja de recibir el diálogo.
5. Si otros usuarios permanecen en `email_user_password`, solo se elimina al usuario actual.

## Pruebas negativas

1. La tarjeta no se oculta ni pierde enlaces a `NXR Fund Source`.
2. Un correo real pendiente conserva el diálogo de contraseña.
3. Una mezcla de correo genérico y real conserva el diálogo.
4. Una lista vacía de correos pendientes no se considera genérica.
5. El hook no ejecuta `set_value`, `delete_doc`, `db.delete` ni modificaciones de datos.
6. El cambio no desactiva la autenticación, los permisos ni la validación SMTP para cuentas reales.

## Seguridad y despliegue

El cambio es de presentación y de composición de la respuesta de arranque. No modifica producción, AWS, Coolify, DNS, secretos, volúmenes ni datos productivos. La publicación en producción requiere respaldo verificable, plan de rollback y validación posterior.

## Criterio de terminado

Los requisitos pasarán a **IMPLEMENTADO Y VALIDADO** únicamente cuando el código y las pruebas estén publicados, las compuertas contractuales y de navegador hayan aprobado, el PR esté fusionado y exista SHA verificable en `main`.
