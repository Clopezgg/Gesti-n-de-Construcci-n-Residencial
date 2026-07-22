# NEXORA — Estado de ejecución

- Última actualización: 2026-07-22
- Repositorio: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama: `nexora-reconstruccion`
- HEAD inicial de `main`: `73c9dadfb81f543e53f45887448fdecbee081850`
- Bloque activo: **BLOQUE 1**
- Bloque 0: **TERMINADO Y PUBLICADO** — `2814acfc655cfbb470e96614cbbc06651023649a`
- Bloque 1: **TERMINADO LOCALMENTE; PUBLICACIÓN EN ESTE COMMIT** — `SELF`
- Producción modificada: **NO**
- Migración histórica: **NO**
- Rama `main` modificada: **NO**

## Evidencia Bloque 0

- Gobierno ejecutable validado: 166 requisitos, 37 máquinas, 32 controles, 9 pruebas comunes y 19 decisiones.
- Rama remota exactamente un commit por delante de `main` al cierre del bloque.

## Evidencia Bloque 1

- `python scripts/validate_nexora_app.py`: aprobado.
- `python -m unittest discover -s nexora_app/nexora/tests -p 'test_app_contract.py' -v`: 4 pruebas aprobadas.
- `python -m compileall -q nexora_app/nexora scripts/validate_nexora_app.py`: aprobado.
- CI real definido con MariaDB 10.6 para instalación, migración, pruebas, desinstalación, reinstalación y convivencia con ERPNext/ConstruControl.

## Siguiente acción exacta

Implementar los DocTypes financieros base del Bloque 2, publicar el commit de modelos y ejecutar los servicios de asignación multifuente sobre MariaDB/Frappe real.
