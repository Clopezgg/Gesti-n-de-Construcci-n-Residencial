# NEXORA — Operación, actualización y respaldo

## Fuente de despliegue

Despliegue únicamente un SHA de `main` con todos los workflows obligatorios aprobados. Registre el SHA antes y después de actualizar. No despliegue desde un directorio local con cambios sin publicar.

## Configuración

Utilice `.env.nexora.example` como referencia y almacene valores reales en el gestor seguro de variables de Coolify o la plataforma operativa. Nunca confirme `.env`, tokens, contraseñas, claves privadas o respaldos productivos.

Defina `NEXORA_BUILD_SHA` con el SHA exacto aprobado de `main`. Para propagarlo a los procesos de aplicación use la definición principal junto con el complemento de identidad:

```bash
docker compose --env-file .env.nexora \
  -f docker-compose.nexora.yml \
  -f deploy/nexora/docker-compose.build-identity.yml \
  up -d --build
```

La API pública no sensible `nexora.build_info.get_build_info` permite comprobar producto, versión, ambiente y SHA sin revelar credenciales.

## Actualización

1. Genere un respaldo con archivos.
2. Confirme espacio disponible y salud de MariaDB/Redis.
3. Obtenga el SHA aprobado de `main` y colóquelo en `NEXORA_BUILD_SHA`.
4. Construya o descargue la imagen/artefacto correspondiente.
5. Ejecute migraciones.
6. Reinicie backend, websocket, workers, scheduler y frontend.
7. Compruebe health checks y logs.
8. Ejecute recorridos básicos: login, dashboard, ingreso controlado, gasto controlado, reporte y evidencia.
9. Ejecute `NEXORA live deployment verification` con la URL y el SHA esperado.

## Verificación del despliegue

La verificación final debe demostrar sobre la URL real:

- `/api/method/ping` responde correctamente;
- la identidad del producto es NEXORA;
- `build_sha` coincide con el SHA aprobado;
- la ruta `/app/nexora-dashboard` existe;
- el manifiesto PWA inicia en el dashboard y usa modo `standalone`.

También puede ejecutarse localmente:

```bash
python scripts/verify_nexora_deployment.py \
  --base-url https://nexora.example.com \
  --expected-sha <SHA_APROBADO>
```

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
- salida de `NEXORA live deployment verification`;
- incidencias y correcciones.
