# NEXORA — Finalización técnica

## Estado

- PR de trabajo: #194
- Rama: `codex/nexora-final-corrections-20260815`
- Base: `main`
- Último HEAD conocido: `5a90d73f2f7189bf627a37d510a2a97995bbf829`
- Último defecto corregido: contrato de conteo de Golden Paths (el registro ya contenía 12; el test contaba solo 10–12 por una condición frágil).

## Regla de certificación

Un bloque solo puede declararse terminado cuando exista código real, interfaz conectada cuando aplique, autorización en servidor, auditoría, manejo de errores, pruebas positivas y negativas, documentación y evidencia de CI/SHA.

## Tramos pendientes de certificación

1. Golden Paths end-to-end en Frappe/MariaDB.
2. Browser/PWA desktop+iPhone.
3. Auditoría final de español visible.
4. Permisos servidor en recorridos críticos.
5. Integraciones reales WhatsApp/SAP (dependencias externas).
6. Staging AWS/Coolify, backup, rollback y observabilidad (dependencia externa/autorización).

## Estado de gates

Los workflows de GitHub Actions para el HEAD actual fueron disparados nuevamente tras corregir el contrato de Golden Paths. No se considera certificado hasta recibir resultados finales verdes.

## Prohibición

No declarar una dependencia externa como IMPLEMENTADO Y VALIDADO sin evidencia de ejecución real.
