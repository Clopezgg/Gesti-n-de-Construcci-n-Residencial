# NEXORA — Estado de ejecución

- Fecha: 2026-07-28
- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama base: `main`
- HEAD base verificado: `b4a1294ea3b6c2675c9aded3ab58264c4f09ffd7`
- Rama técnica: `fix/nexora-funds-layout-email-prompt`
- Producción, AWS, Coolify, DNS, secretos, volúmenes y datos productivos modificados: **NO**
- Migración de registros históricos: **NO**

## Último bloque fusionado — NXR-EXEC-006 / NXR-LGR-0021 / NXR-LGR-0022

Estado: **IMPLEMENTADO Y VALIDADO**.

- PR: `#24`.
- SHA funcional probado: `171fcffd42e29cba3785bb35bb888f6c02e50186`.
- HEAD final certificado del PR: `e6d041537cbb0d26bdf769eb737141d727e7a43e`.
- Commit de fusión publicado en `main`: `6b75f1bb834566701ede2bef5841cd76b44674c6`.

## Bloque actual — NXR-EXEC-007 / NXR-USR-0007

Estado: **IMPLEMENTADO, VALIDACIÓN CI PENDIENTE**.

### Defectos confirmados

- la tarjeta **Fondos y remesas** heredaba la cuadrícula histórica `nxr-balance-row` de cuatro columnas y superponía nombres, fechas y saldos;
- Frappe mostraba **Falta contraseña en la cuenta de correo** porque el usuario actual figuraba en `email_user_password` y tenía un `User Email` genérico pendiente.

### Implementación

- se carga `nexora_dashboard_fixes.css` después de los estilos generales;
- la lista de fondos usa una sola columna y cada fuente separa información flexible de saldo estable;
- nombres largos pueden partirse y los importes no se dividen;
- en móvil, el saldo pasa debajo del nombre;
- se registra `boot_session = ["nexora.boot.suppress_generic_email_password_prompt"]`;
- el hook omite el aviso solo cuando todos los correos pendientes son `admin@nexora.com` o `noreply@nexora.local`;
- una cuenta real pendiente conserva la validación normal de Frappe;
- el hook modifica únicamente la respuesta de arranque y no escribe en `User`, `User Email` ni `Email Account`.

### Pruebas incorporadas

- positiva: la lista de fondos anula la cuadrícula histórica y conserva saldo completo;
- positiva: el correo genérico elimina únicamente al usuario actual de la lista del aviso;
- negativa: un correo real o una mezcla genérico/real mantiene el aviso;
- negativa: la tarjeta no se oculta ni pierde enlaces;
- negativa: el hook no ejecuta operaciones de actualización o eliminación de datos;
- validación pendiente: contratos, linters, Semgrep, Frappe/MariaDB, Patch, escritorio, iPhone y PWA.

### Seguridad

- no se altera la contraseña de inicio de sesión;
- no se desactiva la validación SMTP para cuentas reales;
- no se relajan permisos ni autenticación;
- no se modifica producción ni infraestructura.

## Siguiente acción

Publicar PR hacia `main`, regenerar el inventario canónico, ejecutar todas las compuertas y corregir cualquier fallo real antes de fusionar.
