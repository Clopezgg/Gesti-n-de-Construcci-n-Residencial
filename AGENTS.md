# NEXORA — reglas obligatorias para agentes

> **Este documento está subordinado a [`NEXORA_CONSTITUTION.md`](NEXORA_CONSTITUTION.md)**,
> máxima autoridad técnica y funcional del proyecto. La Constitución define *qué* y *por
> qué*; este documento define *cómo* se opera en este repositorio. Ante cualquier
> contradicción prevalece la Constitución (Capítulo 72). Ninguna regla se duplica aquí: si
> la Constitución ya la fija, este documento la referencia.

## Identidad y fuente de verdad

El producto visible se llama **NEXORA — Gestión Integral de Fondos, Proyectos y Operaciones**.

- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama final y fuente de verdad: `main`
- Motor interno: Frappe/ERPNext
- Producto visible para el usuario ordinario: NEXORA
- ConstruControl: referencia funcional y visual que debe integrarse en NEXORA, no un producto paralelo

El código publicado en `main` prevalece frente a documentos, auditorías o certificaciones históricas. Una afirmación documental no demuestra una función si no existe un recorrido funcional reproducible.

## Inicio obligatorio

Antes de modificar una función:

1. verificar el repositorio, la rama predeterminada y el HEAD remoto de `main`;
2. sincronizar el árbol local sin descartar cambios ajenos;
3. buscar globalmente código, historial, pruebas, páginas, DocTypes, servicios, hooks, fixtures, assets y workflows relacionados;
4. comparar el recorrido visible con la implementación de ConstruControl que pueda reutilizarse;
5. clasificar lo encontrado como conservar, corregir, integrar, simplificar, sustituir o retirar.

No se inicia otra auditoría general ni se reconstruye el producto desde cero.

## Únicas fases de recuperación

### Fase 1 — Recuperación del producto principal

NEXORA debe ser el inicio, la navegación y la experiencia principal. Se integran dashboard, proyectos, fondos, operaciones, contratos, proveedores, evidencias, cuentas y reportes con español claro, diseño responsive y PWA segura.

### Fase 2 — Simplificación operativa

Los ingresos, remesas, depósitos, gastos, pagos y correcciones deben pedir solo datos conocidos por el usuario. El backend conserva trazabilidad, idempotencia, locks, secuencias, permisos, integridad, conciliación y rollback.

### Fase 3 — Integración y publicación definitiva

Se validan recorridos reales, permisos, saldos, errores, persistencia, escritorio, iPhone, PWA, instalación, migraciones, seguridad y CI completo.

No se crean fases, bloques ceremoniales ni fuentes de estado paralelas.

## Principio funcional

«Terminado» lo define el **Capítulo 60 de la Constitución** y no se reescribe aquí: existir
en backend y frontend, validar permisos, conservar auditoría, manejar errores, estar
integrada, tener pruebas satisfactorias, servir en escritorio, móvil y PWA, tener
documentación mínima, no romper funciones relacionadas y ofrecer experiencia empresarial
coherente. Si un punto falla, el bloque continúa abierto.

Condiciones propias de este repositorio, adicionales a esa lista:

- se encuentra desde la navegación normal de NEXORA;
- usa lenguaje comprensible en español;
- funciona con datos reales;
- actualiza saldos, estados y relaciones;
- está incorporada y verificable en `main`.

Compilar, tener un DocType, una ruta o documentación no basta (Capítulo 61).

## Prohibiciones de arquitectura

- No crear otra aplicación, dashboard, navegación, ledger o fuente de saldos paralela.
- No duplicar servicios, DocTypes ni modelos financieros.
- No eliminar una implementación funcional sin demostrar su sustitución y preservar datos, permisos y relaciones.
- No exponer al usuario ordinario campos técnicos, IDs o configuraciones de Frappe que el sistema pueda derivar.
- No conservar el nombre ConstruControl como identidad del producto final.

## Git y publicación

Cada lote debe ser pequeño, coherente y recuperable:

1. revisar `git status` y `git diff`;
2. ejecutar pruebas dirigidas, validadores y formato;
3. crear un commit semántico;
4. publicar inmediatamente en `origin/main`;
5. confirmar que el SHA remoto de `main` contiene el cambio.

No acumular trabajo crítico sin commit y push. No afirmar que un cambio está realizado si solo existe localmente.

Si GitHub rechaza la escritura directa por protección real:

1. conservar el error exacto;
2. usar una sola rama transitoria para ese lote;
3. abrir un único PR hacia `main`;
4. validar y fusionar;
5. confirmar el SHA de `main`;
6. eliminar la rama transitoria cuando sea seguro.

Están prohibidos `git push --force`, `git reset --hard`, `git clean -fd`, rebases destructivos, borrados masivos, lectura o publicación de secretos y cambios de producción, AWS, Coolify o DNS sin autorización específica.

## Calidad

Corregir la causa raíz. No usar `continue-on-error`, exclusiones artificiales, pruebas vacías, mocks autorreferenciales ni silencios masivos.

Según el alcance, ejecutar:

- pruebas unitarias, de integración y negativas;
- validadores del repositorio y de NEXORA;
- sintaxis JavaScript y compilación Python;
- formatter, linter y análisis de seguridad;
- instalación/migración y rollback;
- pruebas visuales, responsive y PWA;
- GitHub Actions del mismo SHA.

La documentación posterior al cambio debe ser breve: problema, archivos, decisión, pruebas, SHA en `main` y limitaciones reales.

## Criterio final

NEXORA solo está terminada cuando sea inequívocamente el producto principal, ConstruControl esté absorbido, Frappe opere como motor interno, los flujos diarios sean sencillos, los saldos sean correctos, escritorio/iPhone/PWA estén validados, CI esté verde y no exista trabajo válido fuera de `main`.
