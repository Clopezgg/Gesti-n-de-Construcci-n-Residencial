# BLOQUE 3 — Esquema, DocFields, Custom Fields y migraciones

## Inventario verificable

- 37 DocTypes runtime declarados en `runtime/definitions_*.json`.
- Ningún nombre de DocType repetido.
- Ningún `fieldname` repetido dentro de una definición.
- Ninguna definición de Custom Field repetida entre instaladores.
- Las únicas reutilizaciones detectadas entre esquema estándar y `expense_setup.py` son `supplier` y `due_date` de `CC Payable Control`; ambas pasan por `_exclude_standard_fields` y no se recrean.

## Control agregado

El runtime real ahora audita todos los DocTypes del contrato instalado y falla cuando encuentra:

1. un `Custom Field` con el mismo `fieldname` que un `DocField` estándar;
2. más de un registro `Custom Field` para la misma pareja DocType/campo;
3. una huella `runtime_contract_sha256` distinta de las definiciones del sistema de archivos.

La comprobación se ejecuta antes del CRUD funcional, por lo que una instalación incoherente no puede producir una validación falsamente positiva.

## Seguridad e idempotencia

- No se elimina ningún campo ni columna.
- No se sobrescriben datos históricos.
- La instalación limpia y dos ejecuciones consecutivas de `bench migrate` ya fueron aprobadas por GitHub Actions.
- La persistencia fue comprobada mediante reinicio del backend y el backup real fue generado y verificado.

## Pruebas

- 114/114 pruebas standalone locales.
- Validadores de repositorio, integración, finalización, arquitectura, datos, producto y gobierno.
- Compilación Python, Ruff y `git diff --check`.
- Pendiente: evidencia remota del nuevo chequeo de metadata en runtime.
