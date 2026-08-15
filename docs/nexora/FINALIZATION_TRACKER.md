# NEXORA — Finalización técnica

## Estado

- PR de trabajo: #194
- Rama: `codex/nexora-final-corrections-20260815`
- Base: `main`
- Último HEAD conocido: `c743c68cba74f930ba1963177daf8cc6113f33f0`

## Regla de certificación

Un bloque solo puede declararse terminado cuando exista código real, interfaz conectada cuando aplique, autorización en servidor, auditoría, manejo de errores, pruebas positivas y negativas, documentación y evidencia de CI/SHA.

## Tramos pendientes de certificación

1. Golden Paths end-to-end en Frappe/MariaDB.
2. Browser/PWA desktop+iPhone.
3. Auditoría final de español visible.
4. Permisos servidor en recorridos críticos.
5. Integraciones reales WhatsApp/SAP (dependencias externas).
6. Staging AWS/Coolify, backup, rollback y observabilidad (dependencia externa/autorización).

## Prohibición

No declarar una dependencia externa como IMPLEMENTADO Y VALIDADO sin evidencia de ejecución real.
