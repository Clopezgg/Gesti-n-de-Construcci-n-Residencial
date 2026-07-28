# NEXORA — Estado de ejecución

- Fecha: 2026-07-28
- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama base: `main`
- Rama técnica fusionada: `fix/nexora-funds-layout-email-prompt`
- Pull Request fusionado: `#25`
- Producción, AWS, Coolify, DNS, secretos, volúmenes y datos productivos modificados: **NO**
- Migración de registros históricos: **NO**

## Último bloque fusionado — NXR-EXEC-007 / NXR-USR-0007

Estado: **IMPLEMENTADO Y VALIDADO**.

### Resultado

- la tarjeta **Fondos y remesas** presenta las fuentes en filas legibles, sin superposición entre nombre, canal, fecha y saldo;
- nombres largos pueden partirse sin invadir el importe;
- los saldos permanecen completos y, en móvil, pasan debajo del nombre;
- el aviso **Falta contraseña en la cuenta de correo** se omite únicamente para identificadores genéricos NEXORA;
- las cuentas reales o combinaciones de correo genérico y real conservan la validación normal de Frappe;
- no se modifican contraseñas ni registros `User`, `User Email` o `Email Account`.

### Evidencia publicada

- PR fusionado: `#25`;
- SHA funcional probado: `8ac970290df4d8cc675ab59d44ce22bd3ec85c27`;
- HEAD final certificado del PR: `deda757fa11163e5126aa0001aa20e6ade2729bf`;
- commit de fusión publicado en `main`: `a3d47d6802944fe9dee6250e6a4d5bd4ba9126dd`;
- NEXORA app, contratos, instalación, rollback, escritorio, iPhone y PWA: run `30330279018`, aprobado;
- Frappe/MariaDB e invariantes financieras: run `30330279078`, aprobado;
- linters y Semgrep: run `30330279040`, aprobado;
- Patch: run `30330279020`, aprobado;
- gobierno NEXORA: run `30330279027`, aprobado;
- documentación requerida: run `30330279052`, aprobado;
- controles estáticos y de parches: runs `30330279148` y `30330279009`, aprobados;
- validación de coexistencia: run `30330279015`, aprobado.

### Pruebas positivas y negativas aprobadas

- la lista de fondos anula la cuadrícula histórica y conserva cada saldo completo;
- nombres largos y saldos se mantienen legibles en escritorio y móvil;
- el correo genérico elimina únicamente al usuario actual de la lista del aviso;
- un correo real o una mezcla genérico/real mantiene el aviso;
- una lista vacía no se considera genérica;
- la tarjeta no se oculta ni pierde enlaces a `NXR Fund Source`;
- el hook no ejecuta operaciones de actualización o eliminación de datos;
- instalación, migración, desinstalación, reinstalación y rollback aprobaron.

### Seguridad

- no se altera la contraseña de inicio de sesión;
- no se desactiva la validación SMTP para cuentas reales;
- no se relajan permisos ni autenticación;
- no se modifica producción ni infraestructura.

## Bloque anterior — NXR-EXEC-006 / NXR-LGR-0021 / NXR-LGR-0022

Estado: **IMPLEMENTADO Y VALIDADO**.

- PR: `#24`.
- SHA funcional probado: `171fcffd42e29cba3785bb35bb888f6c02e50186`.
- Commit de fusión publicado en `main`: `6b75f1bb834566701ede2bef5841cd76b44674c6`.

## Siguiente acción

Desplegar el HEAD vigente de `main` únicamente mediante el procedimiento autorizado de Coolify, con respaldo verificable, rollback por SHA y validación posterior en el sitio real.
