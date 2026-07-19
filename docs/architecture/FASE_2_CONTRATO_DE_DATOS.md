# FASE 2 — Contrato de datos

ConstruControl conserva MariaDB y los volúmenes existentes como persistencia productiva. Supabase permanece únicamente como origen histórico.

## Controles incorporados

- Validación de `definitions_*.json` y `assets.json` antes de actualizar el esquema.
- Huella SHA-256 reproducible del contrato runtime.
- Identidad idempotente mediante `source_key`.
- Conservación de `source_id`, `payload_json` e `is_logically_deleted`.
- Normalización de fechas ISO-8601 para MariaDB.
- Una sola migración activa por sitio mediante bloqueo de MariaDB.
- Respaldo Bench obligatorio antes de la importación real.
- Conciliación entre cantidades de origen y destino.
- Reversión de la transacción cuando una importación no concluye correctamente.
- Conservación lógica de usuarios duplicados y remapeo al registro canónico.
- Pruebas automáticas del contrato de datos en GitHub Actions.

## Orden de ejecución

```text
validar archivo
→ comprobar huella
→ crear respaldo
→ importar con idempotencia
→ conciliar
→ recalcular saldos e inventario
→ confirmar resultado
```

## Reglas vinculantes

1. Los cambios futuros deben mantener la compatibilidad con los datos migrados.
2. Los campos nuevos deben instalarse de forma repetible.
3. Los movimientos financieros deben conservar trazabilidad.
4. Las credenciales permanecen fuera de GitHub.
5. AWS y Coolify reciben el sistema únicamente desde `main`.
6. Los volúmenes productivos permanecen intactos.

## Aceptación

- [x] Contrato runtime versionado.
- [x] Validación previa del esquema.
- [x] Bloqueo contra migraciones simultáneas.
- [x] Idempotencia y conciliación.
- [x] Respaldo y reversión.
- [x] Pruebas contractuales integradas.
- [ ] GitHub Actions confirmado para el último commit.
- [ ] Imagen `linux/amd64` confirmada.

Durante esta fase no se ha ejecutado un despliegue ni se han modificado datos productivos.
