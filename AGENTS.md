# ConstruControl — contexto operativo

## Producto

ConstruControl es el producto privado para controlar integralmente una obra residencial. ERPNext/Frappe v15 es el motor interno; la experiencia visible debe ser única, coherente, en español y usable desde escritorio e iPhone.

## Arquitectura canónica

- Producción: AWS EC2 x86_64, Coolify y `docker-compose.yml`.
- Runtime: ERPNext 15.117.0 / Frappe 15, MariaDB 10.6, Redis, backend, workers, scheduler, WebSocket, frontend y backup.
- Datos: MariaDB es la fuente productiva; Supabase es únicamente origen histórico de migración.
- Dominios: US01, FI01, FI02, PR01, CO01, MM01, MM02, MIGO, QC01, CL01, BI01, AU01 y MIG.
- Todo dato crítico, permiso y transición se valida en servidor y con alcance de proyecto.

## Git y publicación

- Único repositorio: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`.
- Única rama de trabajo: `reconstruccion-definitiva-construcontrol`; único PR: #9; `main` está protegida.
- Prohibidos: otra rama o PR, force push, amend publicado, reescritura, cambios directos a `main`, escritores concurrentes y publicación desde Actions.
- Los commits son semánticos y agrupan una causa raíz o dominio completo.
- No se fusiona, etiqueta ni limpia ramas hasta certificar el mismo SHA.

## Comandos de validación

```bash
python scripts/generate_file_inventory.py --check
python scripts/validate_repository.py
python scripts/validate_construcontrol_architecture.py
python scripts/validate_construcontrol_integration.py
python scripts/validate_construcontrol_completion.py
python scripts/validate_construcontrol_data_contract.py
python scripts/validate_construcontrol_product.py
python -m unittest discover -s erpnext/construcontrol/tests -p 'test_*_standalone.py' -v
python -m compileall -q erpnext/construcontrol scripts
pre-commit run --all-files --show-diff-on-failure
```

Pre-commit debe aprobar dos veces consecutivas sin modificar el árbol. La certificación final es Semantic → Linters → Semgrep → Freeze → A1 → A2 → A3 → A4 → B → C → FINAL → AUDIT_1_TO_1.

## Seguridad y terminado

- No tocar producción, secretos, respaldos ni volúmenes; nunca ejecutar `docker compose down -v` en producción.
- No eliminar código o datos sin inventario de referencias, migración, compatibilidad y rollback.
- `APROBADO` exige prueba funcional específica, prueba negativa, artifact y SHA exacto; `NO DEMOSTRADO` no es aprobación.
- Terminado significa: arquitectura y datos coherentes, permisos por proyecto, UX escritorio/iPhone, PWA/WebSocket, backup/restore/migración, 224 requisitos demostrados, cadena completa verde, PR #9 fusionado, tag `construcontrol-v1.0.0`, ZIP reproducible con SHA-256 y única rama remota `main`.
