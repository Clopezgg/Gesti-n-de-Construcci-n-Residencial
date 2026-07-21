# BLOQUE 3 — Esquema, DocFields, Custom Fields y migraciones

## Inventario verificable

- 37 DocTypes runtime declarados en `runtime/definitions_*.json`.
- 125 registros `Custom Field` instalados y auditados en el entorno aislado.
- Ningún nombre de DocType repetido.
- Ningún `fieldname` repetido dentro de una definición.
- Ninguna definición de Custom Field repetida entre instaladores.
- Cero colisiones entre `DocField` estándar y `Custom Field`.
- Las reutilizaciones `supplier` y `due_date` de `CC Payable Control` pasan por `_exclude_standard_fields` y no se recrean.

## Control agregado

El runtime real audita todos los DocTypes del contrato instalado y falla cuando encuentra:

1. un `Custom Field` con el mismo `fieldname` que un `DocField` estándar;
2. más de un registro `Custom Field` para la misma pareja DocType/campo;
3. una huella `runtime_contract_sha256` distinta de las definiciones del sistema de archivos.

La comprobación se ejecuta antes del CRUD funcional, por lo que una instalación incoherente no puede producir una validación falsamente positiva.

## Evidencia remota

El entorno aislado publicado para el PR #9 devolvió:

- `doctypes: 37`;
- `custom_fields: 125`;
- `collisions: 0`;
- `duplicate_custom_fields: 0`;
- `contract_recorded: true`;
- `status: 0`.

Además aprobó:

- instalación limpia;
- dos ejecuciones consecutivas de `bench migrate`;
- CRUD y conciliación FI01/FI02/FI03;
- límites de permisos por proyecto;
- cierre semanal;
- persistencia tras reiniciar el backend;
- backup real con base de datos, archivos públicos y privados;
- construcción y verificación `linux/amd64`.

## Seguridad e idempotencia

- No se elimina ningún campo ni columna.
- No se sobrescriben datos históricos.
- Las migraciones reutilizan campos estándar cuando corresponden.
- La huella del contrato queda registrada y verificada después de migrar.
- Los workflows de evidencia estática y runtime pueden ejecutarse directamente sobre la rama exclusiva, sin modificar `main`.

## Pruebas

- 114/114 pruebas standalone aprobadas.
- Siete validadores de repositorio, integración, finalización, arquitectura, datos, producto y gobierno.
- Compilación Python, sintaxis JavaScript, YAML, Ruff y linters aprobados.
- Runtime, migración repetida, persistencia y backup aprobados.

## Evidencia Git

- Auditoría de metadata: `4df16b97add1d352755fce128beeb4d97965df28`.
- CI estática de rama: `66393fd55351a48696953c7ab483bf398ac53166`.
- CI runtime de rama: `3bc75624b4ac2e4c5816a7d1b3ae4a201c14b0e3`.
- Pull Request: #9.

## Estado

BLOQUE 3 completado, publicado y validado. `main` permanece sin modificaciones de esta ejecución.
