# Publicación en GitHub

## Revisión previa

```bash
python scripts/validate_repository.py
python erpnext/construcontrol/tests/test_schema_standalone.py -v
git status --short
git diff --check
```

Confirme que no existen `.env`, exports, respaldos, ZIP, `sites/`, logs, credenciales ni archivos de evidencia. El `.gitignore` cubre esos grupos y `.gitattributes` fija LF para scripts Linux.

## Crear y subir el repositorio

```bash
git init
git branch -M main
git add .
git status --short
git commit -m "feat: consolidate ConstruControl on ERPNext 15"
git remote add origin https://github.com/USUARIO/REPOSITORIO.git
git push -u origin main
```

No use `git add -f` para incluir datos ignorados. Si un secreto fue añadido alguna vez, rótelo y elimínelo del historial; borrarlo en un commit posterior no lo protege.

## Configuración recomendada

1. Proteja `main`: PR obligatorio, un revisor y check **ConstruControl validation** obligatorio.
2. Active secret scanning, push protection y Dependabot si el plan lo permite.
3. Use GitHub Environments para producción; Render/Supabase deben guardar sus propios secretos, no el repositorio.
4. Etiquete la base: `git tag -s construcontrol-v1.0.0` y publique checksums del ZIP/código, nunca de respaldos privados.
5. Mantenga un remoto `upstream` de ERPNext para revisar actualizaciones; las diferencias ConstruControl están aisladas en módulo, hooks, despliegue y documentación.

## CI incluida

`.github/workflows/construcontrol-validation.yml` valida Python/JSON/patrones de secretos, pruebas del normalizador, YAML de Render y sintaxis de scripts. No sustituye un entorno Frappe con MariaDB/Redis; antes de fusionar a producción debe existir además una prueba de sitio real con `bench migrate` y tests de integración.
