# NEXORA — Estado de ejecución

- Fecha: 2026-07-28
- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama base: `main`
- HEAD base verificado: `b4a1294ea3b6c2675c9aded3ab58264c4f09ffd7`
- Rama técnica: `fix/nexora-funds-layout-email-prompt`
- Pull Request: `#25`
- Producción, AWS, Coolify, DNS, secretos, volúmenes y datos productivos modificados: **NO**
- Migración de registros históricos: **NO**

## Último bloque fusionado — NXR-EXEC-006 / NXR-LGR-0021 / NXR-LGR-0022

Estado: **IMPLEMENTADO Y VALIDADO**.

- PR: `#24`.
- SHA funcional probado: `171fcffd42e29cba3785bb35bb888f6c02e50186`.
- HEAD final certificado del PR: `e6d041537cbb0d26bdf769eb737141d727e7a43e`.
- Commit de fusión publicado en `main`: `6b75f1bb834566701ede2bef5841cd76b44674c6`.

## Bloque actual — NXR-EXEC-007 / NXR-USR-0007

Estado: **CERTIFICADO EN RAMA, FUSIÓN PENDIENTE**.

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

### Pruebas positivas y negativas aprobadas

- la lista de fondos anula la cuadrícula histórica y conserva saldo completo;
- nombres largos y saldos se mantienen legibles en escritorio y móvil;
- el correo genérico elimina únicamente al usuario actual de la lista del aviso;
- un correo real o una mezcla genérico/real mantiene el aviso;
- la tarjeta no se oculta ni pierde enlaces;
- el hook no ejecuta operaciones de actualización o eliminación de datos;
- el dashboard aprobó escritorio Chromium, iPhone WebKit y PWA;
- instalación, migración, desinstalación, reinstalación y rollback aprobaron.

### Evidencia certificada

- SHA funcional probado: `8ac970290df4d8cc675ab59d44ce22bd3ec85c27`;
- NEXORA app y navegador real: run `30329745021`, aprobado;
- Frappe/MariaDB e invariantes financieras: run `30329745006`, aprobado;
- linters y Semgrep: run `30329744988`, aprobado;
- Patch: run `30329745013`, aprobado;
- gobierno NEXORA: run `30329744992`, aprobado;
- documentación requerida: run `30329744990`, aprobado;
- controles estáticos y de parches: runs `30329745024` y `30329744991`, aprobados;
- validación de coexistencia: run `30329744994`, aprobado.

### Seguridad

- no se altera la contraseña de inicio de sesión;
- no se desactiva la validación SMTP para cuentas reales;
- no se relajan permisos ni autenticación;
- no se modifica producción ni infraestructura.

## Siguiente acción

Validar el cierre documental sobre el HEAD final, marcar el PR `#25` listo para revisión y fusionarlo únicamente si las compuertas aplicables continúan aprobadas.
