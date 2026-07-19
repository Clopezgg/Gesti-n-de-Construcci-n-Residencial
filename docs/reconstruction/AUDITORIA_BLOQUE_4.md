# BLOQUE 4 — US01 usuarios, perfiles, roles, permisos y seguridad de backend

## Alcance cerrado

Se consolidó la administración oficial de usuarios sobre los DocTypes nativos `User`, `Has Role` y `User Permission`. `CC User Access` permanece únicamente como registro histórico oculto y no como fuente de autorización.

## Roles canónicos

- `System Manager` → ADMIN
- `ConstruControl Manager` → MANAGER
- `ConstruControl Operator` → OPERATOR
- `ConstruControl Auditor` → AUDITOR
- `ConstruControl Viewer` → VIEWER

El perfil obtiene el rol real del backend y no utiliza el correo electrónico como rol visible.

## Invariantes administrativas

- `Administrator` no puede suspenderse, degradarse ni eliminarse.
- Una cuenta ADMIN no puede ser modificada por un MANAGER.
- La cuenta administrativa en uso no puede degradarse ni suspenderse a sí misma.
- La última cuenta ADMIN habilitada no puede suspenderse, degradarse ni eliminarse.
- Solo `System Manager` puede asignar ADMIN o eliminar usuarios.
- OPERATOR, AUDITOR y VIEWER requieren un proyecto asignado.
- MANAGER y ADMIN conservan alcance administrativo global y no reciben un proyecto limitante artificial.

## Endpoints protegidos

- Lectura: `get_user_center` exige MANAGER o System Manager.
- Creación y edición: `save_user`, método POST.
- Aprobación: `approve_user`, método POST.
- Suspensión y reactivación: `set_user_enabled`, método POST.
- Eliminación: `delete_user`, método POST y System Manager obligatorio.

La autorización se valida en el backend. Ocultar botones o rutas no sustituye estas comprobaciones.

## Acceso directo y alcance por proyecto

La página `construcontrol-users` admite únicamente `System Manager` y `ConstruControl Manager`. Las pruebas ejecutan acceso por backend y validan:

- proyecto asignado permitido;
- proyecto no asignado rechazado;
- OPERATOR con escritura en su proyecto;
- AUDITOR y VIEWER sin escritura;
- usuarios limitados sin acceso al centro administrativo;
- MANAGER con lectura, creación, edición, aprobación y suspensión de usuarios ordinarios;
- MANAGER sin capacidad para asignar ADMIN, modificar ADMIN o eliminar usuarios;
- System Manager con eliminación autorizada, sin posibilidad de desactivar `Administrator`.

## Auditoría

Cada operación de ciclo de vida registra en `CC Audit Log`:

- identidad del actor;
- rol real del actor;
- acción;
- usuario afectado;
- estado anterior y posterior;
- motivo cuando corresponde.

Se validan las acciones CREATE, UPDATE, APPROVE, SUSPEND/REACTIVATE y DELETE.

## Pruebas publicadas

- 119/119 pruebas standalone.
- Siete validadores de repositorio y producto.
- Compilación Python y sintaxis JavaScript.
- Pre-commit y Ruff.
- Semgrep.
- Validación estática de GitHub Actions.
- Contenedor `linux/amd64`.
- Runtime aislado con migración repetida, CRUD, permisos, persistencia y backup.

## Evidencia Git

- Invariantes iniciales: `08d1e043731a2189fcab753a742b07eaa4419104`.
- Pruebas de roles y autorización: `f1d574fa9d250cacd2b3efde0ef37326f158573f`.
- Autorización con identidad acotada: `e017172809bf6451371a336184c32452106a3155`.
- Regresión del contexto de identidad: `786663b20d8dde6d0ef8f8b190324c9a42c06ef9`.
- Limpieza de artefacto temporal: `443afc438d81b97ded45754adddb986152da8099`.
- Checkpoint validado: `0b968247ebf5fc1b1bcf56005c1d7c9ab4b9bcfc`.

## Estado

BLOQUE 4 implementado y publicado. El cierre definitivo se registra únicamente después de verificar los checks remotos del HEAD y mantener el PR #9 abierto y en borrador.
