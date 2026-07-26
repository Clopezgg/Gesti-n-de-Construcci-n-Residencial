# NEXORA — Operación, actualización y respaldo

## Fuente de despliegue

Despliegue únicamente un SHA de `main` con todos los workflows obligatorios aprobados. Registre el SHA antes y después de actualizar. No despliegue desde un directorio local con cambios sin publicar.

## Configuración

Utilice `.env.example` como referencia y almacene valores reales en el gestor seguro de variables de Coolify o la plataforma operativa. Nunca confirme `.env`, tokens, contraseñas, claves privadas o respaldos productivos.

## Actualización

1. Genere un respaldo con archivos.
2. Confirme espacio disponible y salud de MariaDB/Redis.
3. Obtenga el SHA aprobado de `main`.
4. Construya o descargue la imagen/artefacto correspondiente.
5. Ejecute migraciones.
6. Reinicie backend, websocket, workers, scheduler y frontend.
7. Compruebe health checks y logs.
8. Ejecute recorridos básicos: login, dashboard, ingreso controlado, gasto controlado, reporte y evidencia.

## Respaldo

NEXORA incluye la utilidad `scripts/nexora_backup.py` y los scripts de operación declarados en `deploy/nexora/`. El respaldo válido debe incluir base de datos, archivos públicos y privados, configuración de sitio y un manifiesto verificable.

Mantenga varias generaciones y una copia fuera del servidor principal. Un respaldo no se considera válido hasta probar su restauración en un entorno aislado.

## Restauración

1. Detenga escrituras del sitio afectado.
2. Preserve el estado y los logs actuales.
3. Cree un entorno aislado con versiones compatibles.
4. Restaure base de datos y archivos.
5. Ejecute migraciones.
6. Verifique usuarios, permisos, saldos, documentos, evidencias y reportes.
7. Cambie tráfico únicamente después de la aceptación funcional.

No restaure sobre producción sin respaldo previo y autorización operativa.

## Recuperación ante fallo de actualización

Si una actualización falla, no borre volúmenes ni ejecute `docker compose down -v`. Conserve datos, vuelva al SHA anterior aprobado, restaure solo cuando sea necesario y documente la causa raíz.

## Evidencia operativa

Para cada versión conserve:

- SHA de `main`;
- IDs y resultados de workflows;
- digest del artefacto;
- fecha de despliegue;
- resultado de migraciones;
- prueba de backup/restore;
- incidencias y correcciones.
